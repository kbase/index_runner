# KBaseMetagenomes.AnnotatedMetagenomeAssembly indexer
from src.index_runner.es_indexers.indexer_utils import mean, handle_id_to_file
from src.utils.config import config

import tempfile
import json
import gzip
import shutil
import os


def _index_ama(features_file_gz_path, data, ama_id, ver_ama_id, tmp_dir, conf):
    """"""
    publication_titles = [pub[2] for pub in data.get('publications', [])]
    publication_authors = [pub[5] for pub in data.get('publications', [])]
    ama_index = {
        '_action': 'index',
        'doc': {
            'size': data.get('dna_size'),
            'source_id': data.get('source_id'),
            'source': data.get('source'),
            'gc_content': data.get('gc_content'),
            'warnings': data.get('warnings'),
            'num_contigs': data.get('num_contigs'),
            'mean_contig_length': mean(data.get('contig_lengths', [])),
            'external_source_origination_date': data.get('external_source_origination_date'),
            'original_source_file_name': data.get('original_source_file_name'),
            'environment': data.get('environment'),
            'num_features': data.get('num_features'),
            'publication_authors': publication_authors,
            'publication_titles': publication_titles,
            'molecule_type': data.get('molecule_type'),
            'assembly_ref': data.get('assembly_ref'),
            'notes': data.get('notes'),
            # not sure what to do with the following fields.
            # list<Ontology_event> ontology_events;
            # mapping<string, mapping<string, string>> ontologies_present;
        },
        'index': conf['index_name'],
        'id': ama_id
    }
    ama_index['id'] = ama_id
    yield ama_index
    ver_ama_index = dict(ama_index)
    ver_ama_index['id'] = ver_ama_id
    ver_ama_index['index'] = conf['ver_index_name']
    yield ver_ama_index

    if config()['skip_features']:
        # Indexing of AMA features is turned off in the env
        return

    # unzip gzip file.
    features_file_path = os.path.join(tmp_dir, ver_ama_id.replace(':', "_") + ".json")
    with gzip.open(features_file_gz_path, "rb") as f_in:
        with open(features_file_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    with open(features_file_path) as f:
        features = json.load(f)

    for feat in features:
        id_ = feat.get('id')
        ver_feat_id = ver_ama_id + f"::ama_ft::{id_}"
        # calculate gc content for each feature.
        # if feat.get('dna_sequence'):
        #     dna_seq = feat.get('dna_sequence')
        #     feat_gc_content = ((float(dna_seq.lower().count('c')) + float(dna_seq.lower().count('g'))) / len(dna_seq))

        if feat.get('location'):
            contig_ids, starts, strands, stops = zip(*feat.get('location'))
            contig_ids, starts, strands, stops = list(contig_ids), list(starts), list(strands), list(stops)
        else:
            contig_ids, starts, strands, stops = None, None, None, None

        ver_feat_index = {
            '_action': 'index',
            'doc': {
                'id': id_,
                'type': feat.get('type'),
                'size': feat.get('dna_sequence_length'),
                'starts': starts,
                'strands': strands,
                'stops': stops,
                'contig_ids': contig_ids,
                'functions': feat.get('functions'),
                'functional_descriptions': feat.get('functional_descriptions'),
                'warnings': feat.get('warnings'),
                'parent_gene': feat.get('parent_gene'),
                'inference_data': feat.get('inference_data'),
                'dna_sequence': feat.get('dna_sequence'),
                # 'aliases': feat.get('aliases'),
                # 'gc_content': feat_gc_content,
                # Parent ids below
                'parent_id': ver_ama_id,
                'annotated_metagenome_assembly_size': data.get('dna_size'),
                'annotated_metagenome_assembly_num_features': data.get('num_features'),
                'annotated_metagenome_assembly_num_contigs': data.get('num_contigs'),
                'annotated_metagenome_assembly_gc_content': data.get('gc_content')
            },
            'index': conf['ver_features_index_name'],
            'id': ver_feat_id,
        }
        yield ver_feat_index
    # remove unzipped file
    os.remove(features_file_path)


def main(obj_data, ws_info, obj_data_v1, conf):
    """
    Currently indexes following workspace types:
        ci:              KBaseMetagenomes.AnnotatedMetagenomeAssembly-1.0
        narrative(prod): KBaseMetagenomes.AnnotatedMetagenomeAssembly-1.0
    """
    if not obj_data.get('data'):
        raise Exception("no data in object")
    data = obj_data.get('data')
    info = obj_data.get('info')
    workspace_id = info[6]
    object_id = info[0]
    version = info[4]
    ama_id = f"{conf['namespace']}::{workspace_id}:{object_id}"
    ver_ama_id = f"{conf['ver_namespace']}::{workspace_id}:{object_id}:{version}"

    if not data.get('features_handle_ref'):
        raise Exception("AnnotatedMetagenomeAssembly object does not have features_handle_ref"
                        " field. Can not index features to ElasticSearch.")

    features_handle_ref = data.get('features_handle_ref')
    try:
        # Download features file
        tmp_dir = tempfile.mkdtemp()
        features_file_gz_path = os.path.join(tmp_dir, ver_ama_id.replace(':', "_") + ".json.gz")
        handle_id_to_file(features_handle_ref, features_file_gz_path)

        for doc in _index_ama(features_file_gz_path, data, ama_id, ver_ama_id, tmp_dir, conf):
            yield doc
    finally:
        shutil.rmtree(tmp_dir)
