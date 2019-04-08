"""
Consume workspace update events from kafka and publish new indexes.
"""
import json
from confluent_kafka import Producer

from .utils.kafka_consumer import kafka_consumer
from .utils.config import get_config
from .utils.threadify import threadify
from .indexers.main import index_obj

config = get_config()
producer = Producer({'bootstrap.servers': config['kafka_server']})


def main():
    """
    Main consumer of Kafka messages from workspace updates, generating new indexes.
    """
    topics = [config['topics']['workspace_events']]
    for msg_data in kafka_consumer(topics):
        threadify(_process_event, [msg_data])


def _process_event(msg_data):
    """
    Process a new workspace event. This is the main switchboard for handling
    new workspace events. Dispatches to modules in ./event_handlers

    Args:
        msg_data - json data received in the kafka event
    Valid events for msg_data['evtype'] include:
        NEW_VERSION - a new version has been created for an existing object
        NEW_ALL_VERSIONS - a brand new object is created
        PUBLISH - object is made public
        DELETE_* - deletion on an object
        COPY_ACCESS_GROUP - index all objects in the workspace
        RENAME_ALL_VERSIONS - rename all versions of an object
        REINDEX_WORKSPACE - index all objects in the workspace
    """
    # Workspace events reference:
    # https://github.com/kbase/workspace_deluxe/blob/8a52097748ef31b94cdf1105766e2c35108f4c41/src/us/kbase/workspace/modules/SearchPrototypeEventHandlerFactory.java#L58  # noqa
    # TODO error loggers to kafka/file/etc
    event_type = msg_data.get('evtype')
    ws_id = msg_data.get('wsid')
    if not ws_id:
        raise RuntimeError(f'Invalid wsid in event: {ws_id}')
    if not event_type:
        raise RuntimeError(f"Missing 'evtype' in event: {msg_data}")
    if event_type not in event_type_handlers:
        raise RuntimeError(f"Unrecognized event {event_type}.")
    event_type_handlers[event_type](msg_data)
    print(f"Handler finished for event {msg_data['evtype']}")


def _run_indexer(msg_data):
    """
    Run the indexer for a workspace event message and produce an event for it.
    This will be threaded and backgrounded.
    """
    result = index_obj(msg_data)
    # Produce an event in Kafka to save the index to elasticsearch
    print('producing to', config['topics']['elasticsearch_updates'])
    producer.produce(
        config['topics']['elasticsearch_updates'],
        json.dumps(result),
        callback=_delivery_report
    )
    producer.poll(60)


# Handler functions for each event type ('evtype' key)
event_type_handlers = {
    'NEW_VERSION': _run_indexer
}


def _delivery_report(err, msg):
    """
    Kafka producer callback.
    """
    # TODO file logger
    if err is not None:
        print(f'Message delivery failed on {msg.topic()}: {err}')
    else:
        print(f'Message delivered to {msg.topic()}')
