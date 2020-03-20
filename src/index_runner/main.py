"""
Main entrypoint for the app and the Kafka topic consumer.
Sends work to the es_indexer or the releng_importer.
Generally handles every message synchronously. Duplicate the service to get more parallelism.
"""
import src.index_runner.releng_importer as releng_importer
import src.index_runner.es_indexer as es_indexer
import src.utils.re_client as re_client
import src.utils.es_utils as es_utils
import src.utils.ws_utils as ws_utils
import src.utils.kafka_utils as kafka_utils
from confluent_kafka import Consumer, KafkaError, Producer
import traceback
import signal
import atexit
import sys
import requests
import time
import json
import os
import logging.handlers
import logging
from src.utils.config import config
from src.utils.service_utils import wait_for_dependencies
from src.utils.state import AppState

logger = logging.getLogger('IR')

consumer = None
producer = None
# Wait up to a minute on shutdown to finish up the kafka producer queue
KAFKA_PRODUCER_FLUSH_TIMEOUT = 60
# Timeout for the call to producer.poll in the main loop
KAFKA_PRODUCER_POLL_TIMEOUT = 0.5
# Upon sending messages, if the queue is full, the send loop will
# poll with a timeout value set below...
KAFKA_PRODUCER_RETRY_TIMEOUT = 10
# ...and retry the send this many times
KAFKA_PRODUCER_RETRY_TRIES = 3
STATE_FILE = '/scratch/indexrunner.state'

app_state = AppState(STATE_FILE)


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


def _close_consumer():
    """
    This will close the network connections and sockets. It will also trigger
    a rebalance immediately rather than wait for the group coordinator to
    discover that the consumer stopped sending heartbeats and is likely dead,
    which will take longer and therefore result in a longer period of time in
    which consumers can’t consume messages from a subset of the partitions.
    """
    if consumer is not None:
        consumer.close()
        logger.info("Closed the Kafka consumer")
    else:
        logger.info("Kafka consumer not available, close skipped")


def _init_producer():
    return Producer({'bootstrap.servers': config()['kafka_server'], 'error_cb': _producer_error_cb})


def _close_producer():
    # Note that the producer error callback will be invoked on timeout (I think).
    logger.info(f'Closing Kafka producer, timeout {KAFKA_PRODUCER_FLUSH_TIMEOUT}s')
    producer.flush(KAFKA_PRODUCER_FLUSH_TIMEOUT)


def _close_kafka(signum=None, stack_frame=None):
    _close_consumer()
    _close_producer()


def _start_kafka():
    global consumer
    global producer
    # Initialize and run the Kafka consumer
    try:
        consumer = _init_consumer()
        producer = _init_producer()
        atexit.register(_close_kafka)
        signal.signal(signal.SIGTERM, _close_kafka)
        signal.signal(signal.SIGINT, _close_kafka)

    except Exception as error:
        logger.error(f'Error setting up Kafka consumer ${str(error)}')
        exit(1)


def main():
    """
    Run the the Kafka consumer and two threads for the releng_importer and es_indexer
    """
    app_state.starting()

    # Wait for dependency services (ES and RE) to be live
    wait_for_dependencies(timeout=180, re_api=config().get('skip_releng', False))
    # Used for re-fetching the configuration with a throttle
    last_updated_minute = int(time.time() / 60)
    if not config()['global_config_url']:
        config_tag = _fetch_latest_config_tag()

    # Database initialization
    es_indexer.init_indexes()
    es_indexer.reload_aliases()

    app_state.ready()

    while True:
        msg = consumer.poll(timeout=0.5)
        producer.poll(KAFKA_PRODUCER_POLL_TIMEOUT)
        # logger.debug(f'PROCESSED (main loop): {processed_count}, PENDING: {len(producer)}')
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
            # TODO: If this message does not parse, what should be done?
            # skip it? (commit then continue)
            # log it? (log, commit, continue)
            # create an error entry? (log error to es, log, commit, continue)
        logger.info(f'Received event: {msg}')
        start = time.time()
        try:
            _handle_msg(msg)
            # Move the offset for our partition
            consumer.commit()
            logger.info(f"Handled {msg['evtype']} message in {time.time() - start}s")
        except Exception as err:
            logger.error(f'Error processing message: {err.__class__.__name__} {err}')
            logger.error(traceback.format_exc())
            # Save this error and message to a topic in Elasticsearch
            es_utils.log_err_to_es(msg, err=err)

    # if monitoring_server:
    #     logging.debug('monitoring stopping')
    #     monitoring_server.stop()


def _handle_msg(msg):
    event_type = msg.get('evtype')
    if not event_type:
        logger.warning(f"Missing 'evtype' in event: {msg}")
        # TODO: we don't want to miss messages, even misconfigured ones, right?
        #       so shouldn't we have an es error entry?
        return
    if event_type in ['REINDEX', 'NEW_VERSION', 'COPY_OBJECT', 'RENAME_OBJECT']:
        if config()['skip_releng']:
            need_in_re = False

        obj = None
        ws_info = kafka_utils.get_workspace_info(msg)
        if need_in_re:
            obj = kafka_utils.get_object_data(msg)
            releng_importer.run_importer(obj, ws_info, msg)

        if obj is None:
            obj_info = kafka_utils.get_object_info(msg)
        else:
            obj_info = obj['info']
        es_indexer.run_indexer(obj, obj_info, ws_info, msg)
    elif event_type == 'REINDEX_WS' or event_type == 'CLONE_WORKSPACE':
        # Reindex all objects in a workspace, overwriting existing data
        for (objid, _) in ws_utils.list_workspace_ids(msg['wsid']):
            _produce({'evtype': 'REINDEX', 'wsid': msg['wsid'], 'objid': objid})
    elif event_type == 'INDEX_NONEXISTENT_WS':
        # Reindex all objects in a workspace without overwriting any existing data
        for (objid, _) in ws_utils.list_workspace_ids(msg['wsid']):
            _produce({'evtype': 'INDEX_NONEXISTENT', 'wsid': msg['wsid'], 'objid': objid})
    elif event_type == 'INDEX_NONEXISTENT':
        # Since relation engine integration is optional, we should try to fetch if disabled
        if config()['skip_releng']:
            need_in_re = False
        else:
            need_in_re = not re_client.check_doc_existence(msg['wsid'], msg['objid'])

        need_in_es = not es_utils.check_doc_existence(msg['wsid'], msg['objid'])

        if need_in_re or need_in_es:
            obj = None
            ws_info = kafka_utils.get_workspace_info(msg)
            if need_in_re:
                obj = kafka_utils.get_object_data(msg)
                releng_importer.run_importer(obj, ws_info, msg)

            if obj is None:
                obj_info = kafka_utils.get_object_info(msg)
            else:
                obj_info = obj['info']
            if need_in_es:
                es_indexer.run_indexer(obj, obj_info, ws_info, msg)
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


def _producer_error_cb(err):
    # TODO: should producer errors not be logged to ES as well?
    logging.error('Producer error: %s' % err)


def _produce(data, topic=config()['topics']['admin_events']):
    """
    Produce a new event message on a Kafka topic and block at most 0.1 for it to get published.
    """

    tries = KAFKA_PRODUCER_RETRY_TRIES
    message = json.dumps(data)
    while tries > 0:
        try:
            producer.produce(topic, message, callback=_delivery_report)
            # Will immediately pop off any fully completed items from the
            # send queue
            # Just housekeeping, really, reducing the load on the main loop.
            # Note that this does not pop off the just-sent message,
            # since producer is async. That will be handled in the main loop.
            # But, just in case, the exception handling will take care of
            # the queue filling up.
            producer.poll(0)
            tries = 0
        except BufferError as e:
            # Handles the case of a full send queue. This can happen if there
            # are > buffer size events in the send queue, which defaults to 10K.
            # This can happen, e.g., when workspace index spins out thousands of
            # indexing requests in quick succession.
            tries = tries - 1
            logger.error((f'BufferError sending kafka message (produce), '
                          'waiting {KAFKA_PRODUCE_RETRY_TIMEOUT}s, retrying {tries - 1} more times'))
            producer.poll(KAFKA_PRODUCER_RETRY_TIMEOUT)
            if tries == 0:
                logger.error(f'Kafka produce could not successfully complete after {KAFKA_PRODUCER_RETRY_TRIES} tries')
                # Reraising this error should cause an error message into ES
                # and will also ensure that if this is part of a kafka consume the
                # upstream message is left in place and not lost.
                raise e


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
    print(f'Logger and level: {logger}')
    print(f'Logging to file: {log_path}')


if __name__ == '__main__':
    # Set up the logger
    # Make the urllib debug logs less noisy
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    init_logger()

    # Run the main thread
    _start_kafka()
    try:
        main()
        app_state.done()
    except Exception as e:
        app_state.error(str(e))
