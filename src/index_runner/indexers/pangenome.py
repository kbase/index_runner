# generator that returns pangenome indexes

_PANGENOME_INDEX_VERSION = 1
_PANGENOME_ORTHOLOG_FAMILY_INDEX_VERSION = 1


def index_pangenome(obj_data, ws_info, obj_data_v1):
    """
    """
    info = obj_data['info']
    data = obj_data['data']

    workspace_id = info[6]
    object_id = info[0]

    yield {
        'doc': {
            'pangenome_id': data.get('id', None),
            'pangenome_name': data.get('name', None),
            'pangenome_type': data.get('type', None),
            'genome_upas': data.get('genome_refs', []),
        },
        'index': 'pangenome:' + str(_PANGENOME_INDEX_VERSION),
        'id': f"{workspace_id}:{object_id}"
    }

    for ortholog_family in data.get('orthologs', []):
        ortholog_id = ortholog_family.get('id', "")

        gene_ids = [ortho[0] for ortho in ortholog_family.get('orthologs', [])]
        # do we want to add fields like creator, creation date etc.?
        yield {
            'doc': {
                'ortholog_id': ortholog_id,
                'ortholog_type': ortholog_family.get('type', None),
                'function': ortholog_family.get('function', None),
                'gene_ids': gene_ids,
            },
            'index': 'pangenome_orthologfamily:' + str(_PANGENOME_ORTHOLOG_FAMILY_INDEX_VERSION),
            'id': f"{workspace_id}:{object_id}:{ortholog_id}",
            'no_defaults': True
        }


def delete_pangenome(obj_data):
    """
    """
    info = obj_data['info']
    data = obj_data['data']

    workspace_id = info[6]
    object_id = info[0]
    yield {
        'index': 'pangenome:' + str(_PANGENOME_INDEX_VERSION),
        'id': f"{workspace_id}:{object_id}",
    }
    for ortholog_family in data.get('orthologs', []):
        ortholog_id = ortholog_family.get('id', "")
        yield {
            'index': 'pangenome_orthologfamily:' + str(_PANGENOME_ORTHOLOG_FAMILY_INDEX_VERSION),
            'id': f"{workspace_id}:{object_id}:{ortholog_id}",
        }
