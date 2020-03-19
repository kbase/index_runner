"""Elasticsearch API client utilities."""
import json
import requests
import hashlib

from src.utils.config import config
import src.index_runner.es_indexer as es_indexer

# Initialize configuration data
_PREFIX = config()['elasticsearch_index_prefix']
_ES_URL = "http://" + config()['elasticsearch_host'] + ":" + str(config()['elasticsearch_port'])


def check_doc_existence(wsid, objid):
    """Check if a document exists on elasticsearch based on workspace and object id."""
    _id = f"WS::{wsid}:{objid}"
    resp = requests.post(
        _ES_URL + f"/{_PREFIX}.*/_search",
        data=json.dumps({'query': {'term': {'_id': _id}}}),
        params={'size': 0},
        headers={'Content-Type': 'application/json'}
    )
    if not resp.ok:
        raise RuntimeError(f"Unexpected elasticsearch server error:\n{resp.text}")
    resp_json = resp.json()
    total = resp_json['hits']['total']['value']
    return total > 0


def log_err_to_es(msg, err=None):
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
