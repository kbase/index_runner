"""
Main entrypoint for the app and the Kafka topic consumer.
Sends work to the es_indexer or the releng_importer.
Generally handles every message synchronously. Duplicate the service to get more parallelism.
"""
import logging
import logging.handlers
import os
import json
import time
import requests
import sys
import atexit
import signal
import traceback
import hashlib
from confluent_kafka import Consumer, KafkaError, Producer
from kbase_workspace_client import WorkspaceClient
from kbase_workspace_client.exceptions import WorkspaceResponseError

import src.utils.es_utils as es_utils
import src.utils.re_client as re_client
import src.index_runner.es_indexer as es_indexer
import src.index_runner.releng_importer as releng_importer
from src.utils.config import config
from src.utils.service_utils import wait_for_dependencies

logger = logging.getLogger('IR')
ws_client = WorkspaceClient(url=config()['kbase_endpoint'], token=config()['ws_token'])
_KAFKA_PRODUCE_RETRIES = 5


def _init_consumer():
    """
    Initialize a Kafka consumer instance
    """
    consumer = Consumer({
        'bootstrap.servers': config()['kafka_server'],
        'group.id': config()['kafka_clientgroup'],
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False
    })
    topics = [
        config()['topics']['workspace_events'],
        config()['topics']['admin_events']
    ]
    logger.info(f"Subscribing to: {topics}")
    logger.info(f"Client group: {config()['kafka_clientgroup']}")
    logger.info(f"Kafka server: {config()['kafka_server']}")
    consumer.subscribe(topics)
    return consumer


def _close_consumer(signum=None, stack_frame=None):
    """
    This will close the network connections and sockets. It will also trigger
    a rebalance immediately rather than wait for the group coordinator to
    discover that the consumer stopped sending heartbeats and is likely dead,
    which will take longer and therefore result in a longer period of time in
    which consumers can’t consume messages from a subset of the partitions.
    """
    consumer.close()
    logger.info("Closed the Kafka consumer")


# Initialize and run the Kafka consumer
consumer = _init_consumer()
atexit.register(_close_consumer)
signal.signal(signal.SIGTERM, _close_consumer)
signal.signal(signal.SIGINT, _close_consumer)


def main():
    """
    Run the the Kafka consumer and two threads for the releng_importer and es_indexer
    """
    # Remove the ready indicator file if it has been written on a previous boot
    if os.path.exists(config()['proc_ready_path']):
        os.remove(config()['proc_ready_path'])
    # Wait for dependency services (ES and RE) to be live
    wait_for_dependencies(timeout=180)
    # Used for re-fetching the configuration with a throttle
    last_updated_minute = int(time.time() / 60)
    if not config()['global_config_url']:
        config_tag = _fetch_latest_config_tag()
    # Database initialization
    es_indexer.init_indexes()
    es_indexer.reload_aliases()
    # Touch a temp file indicating the daemon is ready
    with open(config()['proc_ready_path'], 'w') as fd:
        fd.write('')

    while True:
        msg = consumer.poll(timeout=0.5)
        if msg is None:
            continue
        curr_min = int(time.time() / 60)
        if not config()['global_config_url'] and curr_min > last_updated_minute:
            # Check for configuration updates
            latest_config_tag = _fetch_latest_config_tag()
            last_updated_minute = curr_min
            if config_tag is not None and latest_config_tag != config_tag:
                config(force_reload=True)
                config_tag = latest_config_tag
                es_indexer.reload_aliases()
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                logger.info('End of stream.')
            else:
                logger.error(f"Kafka message error: {msg.error()}")
            continue
        val = msg.value().decode('utf-8')
        try:
            msg = json.loads(val)
        except ValueError as err:
            logger.error(f'JSON parsing error: {err}')
            logger.error(f'Message content: {val}')
        logger.info(f'Received event: {msg}')
        start = time.time()
        try:
            _handle_msg(msg)
            # Move the offset for our partition
            consumer.commit()
            _log_msg_to_elastic(msg)
            logger.info(f"Handled {msg['evtype']} message in {time.time() - start}s")
        except Exception as err:
            logger.error(f'Error processing message: {err.__class__.__name__} {err}')
            logger.error(traceback.format_exc())
            # Save this error and message to a topic in Elasticsearch
            _log_err_to_es(msg, err=err)


def _handle_msg(msg):
    event_type = msg.get('evtype')
    if not event_type:
        logger.warning(f"Missing 'evtype' in event: {msg}")
        return
    if event_type in ['REINDEX', 'NEW_VERSION', 'COPY_OBJECT', 'RENAME_OBJECT']:
        obj = _fetch_obj_data(msg)
        ws_info = _fetch_ws_info(msg)
        if not config()['skip_releng']:
            releng_importer.run_importer(obj, ws_info, msg)
        es_indexer.run_indexer(obj, ws_info, msg)
    elif event_type == 'REINDEX_WS' or event_type == 'CLONE_WORKSPACE':
        # Reindex all objects in a workspace, overwriting existing data
        for objinfo in ws_client.generate_obj_infos(msg['wsid'], admin=True):
            objid = objinfo[0]
            _produce({'evtype': 'REINDEX', 'wsid': msg['wsid'], 'objid': objid})
    elif event_type == 'INDEX_NONEXISTENT_WS':
        # Reindex all objects in a workspace without overwriting any existing data
        for objinfo in ws_client.generate_obj_infos(msg['wsid'], admin=True):
            objid = objinfo[0]
            _produce({'evtype': 'INDEX_NONEXISTENT', 'wsid': msg['wsid'], 'objid': objid})
    elif event_type == 'INDEX_NONEXISTENT':
        # Import to RE if we are not skipping RE and also it does not exist in the db
        re_required = not config()['skip_releng'] and not re_client.check_doc_existence(msg['wsid'], msg['objid'])
        # Index in elasticsearch if it does not exist there by ID
        es_required = not es_utils.check_doc_existence(msg['wsid'], msg['objid'])
        if not re_required and not es_required:
            # Skip any indexing/importing of this object
            return
        # We need to either index or import the object
        obj = _fetch_obj_data(msg)
        ws_info = _fetch_ws_info(msg)
        if re_required:
            releng_importer.run_importer(obj, ws_info, msg)
        if es_required:
            es_indexer.run_indexer(obj, ws_info, msg)
    elif event_type == 'OBJECT_DELETE_STATE_CHANGE':
        # Delete the object on RE and ES. Synchronous for now.
        es_indexer.delete_obj(msg)
        if not config()['skip_releng']:
            releng_importer.delete_obj(msg)
    elif event_type == 'WORKSPACE_DELETE_STATE_CHANGE':
        # Delete everything in RE and ES under this workspace
        es_indexer.delete_ws(msg)
        if not config()['skip_releng']:
            releng_importer.delete_ws(msg)
    elif event_type == 'SET_GLOBAL_PERMISSION':
        # Set the `is_public` permissions for a workspace
        es_indexer.set_perms(msg)
        if not config()['skip_releng']:
            releng_importer.set_perms(msg)
    elif event_type == 'RELOAD_ELASTIC_ALIASES':
        # Reload aliases on ES from the global config file
        es_indexer.reload_aliases()
    else:
        logger.warning(f"Unrecognized event {event_type}.")
        return


def _log_msg_to_elastic(msg):
    """
    Save every message consumed from Kafka to an Elasticsearch index for logging purposes.
    """
    # The key is a hash of the message data body
    # The index document is the error string plus the message data itself
    ts = msg.get('time', int(time.time() * 1000))
    es_indexer._write_to_elastic([{
        'index': config()['msg_log_index_name'],
        'id': ts,
        'doc': msg
    }])


def _fetch_obj_data(msg):
    if not msg.get('wsid') or not msg.get('objid'):
        raise RuntimeError(f'Cannot get object ref from msg: {msg}')
    obj_ref = f"{msg['wsid']}/{msg['objid']}"
    if msg.get('ver'):
        obj_ref += f"/{msg['ver']}"
    try:
        obj_data = ws_client.admin_req('getObjects', {
            'objects': [{'ref': obj_ref}]
        })
    except WorkspaceResponseError as err:
        logger.error(f'Workspace response error: {err.resp_data}')
        # Workspace is deleted; ignore the error
        if (err.resp_data and isinstance(err.resp_data, dict)
                and err.resp_data['error'] and isinstance(err.resp_data['error'], dict)
                and err.resp_data['error'].get('code') == -32500):
            return
        else:
            raise err
    result = obj_data['data'][0]
    if not obj_data or not obj_data['data'] or not obj_data['data'][0]:
        logger.error(obj_data)
        raise RuntimeError("Invalid object result from the workspace")
    return result


def _fetch_ws_info(msg):
    if not msg.get('wsid'):
        raise RuntimeError(f'Cannot get workspace info from msg: {msg}')
    try:
        ws_info = ws_client.admin_req('getWorkspaceInfo', {
            'id': msg['wsid']
        })
    except WorkspaceResponseError as err:
        logger.error(f'Workspace response error: {err.resp_data}')
        raise err
    return ws_info


def _fetch_latest_config_tag():
    """
    Using the Github release API, check for a new version of the config.
    https://developer.github.com/v3/repos/releases/
    """
    github_release_url = config()['github_release_url']
    if config()['github_token']:
        headers = {'Authorization': f"token {config()['github_token']}"}
    else:
        headers = {}
    try:
        resp = requests.get(url=github_release_url, headers=headers)
    except Exception as err:
        logging.error(f"Unable to fetch indexer config from github: {err}")
        # Ignore any error and continue; try the fetch again later
        return None
    if not resp.ok:
        logging.error(f"Unable to fetch indexer config from github: {resp.text}")
        return None
    data = resp.json()
    return data['tag_name']


def _produce(data, topic=config()['topics']['admin_events']):
    """
    Produce a new event messagew on a Kafka topic and block at most 60s for it to get published.
    """
    producer = Producer({'bootstrap.servers': config()['kafka_server']})
    tries = 0
    while True:
        try:
            producer.produce(topic, json.dumps(data), callback=_delivery_report)
            producer.flush()
            break
        except BufferError:
            if tries == _KAFKA_PRODUCE_RETRIES:
                raise RuntimeError("Unable to produce a Kafka message due to BufferError")
            logger.error("Received a BufferError trying to produce a message on Kafka. Retrying..")
            tries += 1


def _log_err_to_es(msg, err=None):
    """Log an indexing error in an elasticsearch index."""
    # The key is a hash of the message data body
    # The index document is the error string plus the message data itself
    _id = hashlib.blake2b(json.dumps(msg).encode('utf-8')).hexdigest()
    es_indexer._write_to_elastic([
        {
            'index': config()['error_index_name'],
            'id': _id,
            'doc': {'error': str(err), **msg}
        }
    ])


def _delivery_report(err, msg):
    if err is not None:
        logger.error(f'Message delivery failed:\n{err}')
    else:
        logger.info(f'Message delivered to {msg.topic()}')


def init_logger():
    """
    Initialize log settings. Mutates the `logger` object.
    Write to stdout and to a local rotating file.
    Logs to tmp/app.log
    """
    # Set the log level
    level = os.environ.get('LOGLEVEL', 'DEBUG').upper()
    logger.setLevel(level)
    logger.propagate = False  # Don't print duplicate messages
    logging.basicConfig(level=level)
    # Create the formatter
    fmt = "%(asctime)s %(levelname)-8s %(message)s (%(filename)s:%(lineno)s)"
    time_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, time_fmt)
    # File handler
    os.makedirs('tmp', exist_ok=True)
    # 1mb max log file with 2 backups
    log_path = 'tmp/app.log'
    file_handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=1048576, backupCount=2)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    # Stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)
    logger.info(f'Logger and level: {logger}')
    logger.info(f'Logging to file: {log_path}')


if __name__ == '__main__':
    # Set up the logger
    # Make the urllib debug logs less noisy
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    init_logger()
    # Run the main thread
    main()
