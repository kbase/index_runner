# Configurations in the Index Runner
There are a few different configuration needs in the index runner which are fulfilled by different files. all the configurations live in the `spec` folder.

## `config.yaml`
This file contains mostly start up information for elasticsearch as well as some more permanent configurable information. the fields are outlined in the sections below.

### ws_type_to_indexes
This serves as a simple mapping from the workspace defined datatype name of an object to the index naming convention that is used in elasticsearch. This is primarily used by the sdk indexers.
### sdk_indexer_apps
A mapping from workspace object type to the SDK application that can be used as an indexer.
```yaml
  KBaseMatrices.MetaboliteMatrix:
    sdk_app: kbasematrices_indexer
    sdk_func: run_kbasematrices_indexer
    sub_obj_index: attribute_mapping
```
the `sdk_app` and `sdk_func` fields are required and must correspond to a registered sdk application. the `sub_obj_index` field exists for communicating an additional sub object index, should the indexer produce sub object indices.
### ws_subobjects
a list of the indexes that are currently defined as subobjects. These are indexes that are produced by an indexer that already produces a workspace datatype index. A good example is the genome feature indexer.
### genome_features_current_index_name
a quirk used for genome features search.
### global_mappings
defines the fields that are used by all indexers.
### latest_versions
The latest version of each indexer type.
### aliases
Alias mappings that are written into Elasticsearch on start-up. Can be any arbitrary mapping.
### mappings
The elasticsearch defined mappings that are used to instantiate the indices. For more details on the specifics of what values in these mapping mean, read the [elasticsearch documentation](https://www.elastic.co/guide/en/elasticsearch/reference/7.15/mapping-types.html). 
### ws_type_blacklist
List of data types that are permanently blacklisted. These are typically functionally dead datatypes
## `ama_config.yaml`
This configuration exists as a means of creating a dedicated indexer for narratives. It follows the same conventions as the `config.yaml` file.

## `elasticsearch_modules.yaml`
This file specifices all the configuration needs for the 
for more detail on this configuration, read the `releng_vs_es_indexers.md` documentation.

## `narrative_config.yaml`
similarly to the ama_config, this configuration exists as a means of creating a dedicated indexer for narratives. It follows the same conventions as the `config.yaml` file.