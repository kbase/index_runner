from src.index_runner.es_indexers.indexer_utils import mean
import src.utils.ws_utils as ws_utils

_NAMESPACE = "WS"
_ASSEMBLY_INDEX_VERSION = 1
_ASSEMBLY_INDEX_NAME = 'assembly_' + str(_ASSEMBLY_INDEX_VERSION)


def index_assembly(obj_data, ws_info, obj_info_v1):
    """
    Currently Handles the follownig workspace types:
         KBaseGenomeAnnotations.Assembly-6.0
    """
    data = obj_data['data']
    obj_info = obj_data['info']
    workspace_id = obj_info[6]
    object_id = obj_info[0]

    # get mean contig length
    if data.get('contigs'):
        # we do not include the contig if it does not store the requisite field
        mean_contig_length = mean([contig.get('length') for _, contig
                                   in data['contigs'].items() if contig.get('length')])
        percent_complete_contigs = mean([contig.get('is_complete') for _, contig
                                         in data['contigs'].items() if contig.get('is_complete')])
        percent_circle_contigs = mean([contig.get('is_circ') for _, contig
                                       in data['contigs'].items() if contig.get('is_circ')])
    else:
        mean_contig_length, percent_complete_contigs, percent_circle_contigs = None, None, None
    yield {
        '_action': 'index',
        'doc': {
            "assembly_name": data.get("name", None),
            "mean_contig_length": mean_contig_length,
            "percent_complete_contigs": percent_complete_contigs,
            "percent_circle_contigs": percent_circle_contigs,
            "assembly_id": data.get('assembly_id', None),
            "gc_content": data.get('gc_content', None),
            "size": data.get('dna_size', None),
            "num_contigs": data.get('num_contigs', None),
            "taxon_ref": data.get('taxon_ref', None),
            "external_origination_date": data.get('external_source_origination_date', None),
            "external_source_id": data.get('external_source_id', None),
            "external_source": data.get('external_source', None),
        },
        'index': _ASSEMBLY_INDEX_NAME,
        'id': f"{_NAMESPACE}::{workspace_id}:{object_id}",
    }
