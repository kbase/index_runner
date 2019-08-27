"""
This is the entrypoint for running the app. A parent supervisor process that
launches and monitors child processes.

Architecture:
    Nodes:
        - index_runner -- consumes workspace and admin indexing events from kafka, runs indexers.
        - es_writer -- receives updates from index_runner and bulk-updates elasticsearch.
    The index_runner and es_writer run in separate workers with message queues in between.
"""
import time
import requests
import json
from confluent_kafka import Consumer, KafkaError

from src.utils.config import get_config
from src.utils.worker_group import WorkerGroup
from src.index_runner.es_indexer import ESIndexer

_CONFIG = get_config()


def main():
    """
    - Multiple processes run Kafka consumers under the same topic and client group
    - Each Kafka consumer pushes work to one or more es_indexers or releng_importers

    Work is sent from the Kafka consumer to the es_writer or releng_importer via ZMQ sockets.
    """
    # Wait for elasticsearch to be live
    _wait_for_es()
    # Initialize worker group of ESIndexer
    es_indexers = WorkerGroup(ESIndexer, (), count=_CONFIG['zmq']['num_es_indexers'])
    # All worker groups to send kafka messages to
    receivers = [es_indexers]

    # Initialize and run the Kafka consumer
    consumer = Consumer({
        'bootstrap.servers': _CONFIG['kafka_server'],
        'group.id': _CONFIG['kafka_clientgroup'],
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': True
    })
    topics = [
        _CONFIG['topics']['workspace_events'],
        _CONFIG['topics']['indexer_admin_events']
    ]
    print(f"Subscribing to: {topics}")
    print(f"Client group: {_CONFIG['kafka_clientgroup']}")
    print(f"Kafka server: {_CONFIG['kafka_server']}")
    consumer.subscribe(topics)
    while True:
        msg = consumer.poll(timeout=0.5)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                print('End of stream.')
            else:
                print(f"Kafka message error: {msg.error()}")
            continue
        val = msg.value().decode('utf-8')
        try:
            data = json.loads(val)
        except ValueError as err:
            print(f'JSON parsing error: {err}')
            print(f'Message content: {val}')
        for receiver in receivers:
            receiver.queue.put(data)


def _wait_for_es():
    """Block and wait for elasticsearch."""
    timeout = 180  # in seconds
    start_time = int(time.time())
    es_started = False
    while not es_started:
        # Check for Elasticsearch
        try:
            requests.get(_CONFIG['elasticsearch_url']).raise_for_status()
            es_started = True
        except Exception:
            print('Unable to connect to elasticsearch, waiting..')
            time.sleep(5)
            if (int(time.time()) - start_time) > timeout:
                raise RuntimeError(f"Failed to connect to other services in {timeout}s")
    print('Services started! Now starting the app..')


if __name__ == '__main__':
    print('before main..')
    main()
