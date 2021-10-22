# Relation Engine vs Elasticsearch Indexers
This document describes and highlights the differences between the relation engine and elastic search indexers.
## Relation Engine indexers
### type specific indexers
Relation Engine (RE) indexers live in the `src/index_runner/releng` folder. They conform to the following standards:
All ES indexers must have a main function which has the following arguments:
```python
def process_object_type(obj_ver_key, obj_data):
```

### adding a type specific indexer
Adding a type specific indexer requires adding a new file to `src/index_runner/releng` that writes the documents to ArangoDB directy using the RE API. Functions in `src/utils/re_client.py` will likely be useful.

These indexers are more freeform and just require that the links are written to Relation Engine. Configuration details are generally stored in the file itself.

### default behaviour
By default, the re indexers will create shadow objects and links of workspace objects in ArangoDB using the relation enginer API. All objects including those that have type specific indexers have the same pieces indexed. For more details see lines 38-52 in the `src/index_runner/releng/import_obj.py` file.

## Elasticsearch indexers
### Outputs
All forms of es indexing conform to a format when producing indexes.
```python
{
	'_action': "index",  # the action to take with the document, typically "index"
	'doc': {"key": "value"},  # the document fields to index
	'index': "es_index_1",  # taken from configuration
	'id': "WS::1:2"  # the identifier to use in elasticsearch, must be unique for this index.
}
```

### type specific indexers
Elasticsearch (ES) type specific indexers live in the `src/index_runner/es_indexers` folder. They conform to the following standards:
All ES indexers must have  `main` function which has the following arguments
```python
def main(obj_data, ws_info, obj_data_v1, conf):
``` 
`obj_data` = the object data as retrieved from the get_objects2 workspace call
`ws_info` = the workspace info as retrieved from the get_workspace_info3 workspace call
`obj_data_v1` = the object data of the first version of the object as retrieved from the get_objects2 workspace call
`conf` = the configuration as defined in `src/utils/config.py`

### adding a type specific indexer
To add a new type specific indexer you must add to a few configurations for the indexer to be operational.

The `spec/elasticsearch_modules.yaml` file contains all the necessary linking for an indexer to become integrated. Here is an example:

```yaml
  - module: KBaseGenomes
    type: Genome
    source: src.index_runner.es_indexers.genome
    config:
      namespace: WS
      index_name: genome_2
      features_index_name: genome_features_3
```
the `module` and `type` fields refer to the KBase object type.
the `source` should link to the import location of the indexer, which should live in the `src.index_runner.es_indexers` folder. notice that there is also a config section, which is the information that is passed to the indexer in the `conf` argument. There are a few fields that are generally useful there, but other configuration pieces can be added there.

### defualt behaviour
There is default indexer for all indexers that do not fall in the permanent blacklist or the configuration defined blacklist. The standard fields are as follows:
```python
{
    "creator": obj_data["creator"],
    "access_group": ws_id,
    "obj_name": obj_data['info'][1],
    "shared_users": shared_users,
    "timestamp": obj_data['epoch'],
    "creation_date": v1_info[3],
    "is_public": is_public,
    "version": version,
    "obj_id": obj_id,
    "copied": copy_ref,
    "tags": tags,
    "obj_type_version": type_version,
    "obj_type_module": type_module,
    "obj_type_name": type_name
}
```
These standard fields are also included in type specific indexers.
