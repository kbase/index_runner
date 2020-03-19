import sys
from bs4 import BeautifulSoup
from markdown2 import Markdown
import logging
from datetime import datetime

from src.utils.get_path import get_path
from src.index_runner.es_indexers import indexer_utils

logger = logging.getLogger('IR')

_NAMESPACE = "WS"
_MARKDOWNER = Markdown()
_NARRATIVE_INDEX_VERSION = 1
_NARRATIVE_INDEX_NAME = 'narrative_' + str(_NARRATIVE_INDEX_VERSION)


def _get_is_temporary(ws_metadata):
    is_temporary_string = ws_metadata.get('is_temporary')
    if is_temporary_string is not None:
        if is_temporary_string == 'true':
            return True
        else:
            return False


def _get_is_narratorial(ws_metadata):
    if ws_metadata.get('narratorial') == '1':
        return True
    else:
        return False


def iso8601_to_epoch(time_string):
    return round(datetime.strptime(time_string, '%Y-%m-%dT%H:%M:%S%z').timestamp())


def index_narrative(obj_data, ws_info, obj_info_v1):
    """
    Index a narrative object on save.
    We index the latest narratives for:
        - title and author
        - cell content
        - object names and types
        - created and updated dates
        - total number of cells
    """
    obj_info = obj_data['info']
    [obj_id, obj_name, _, _, _, _, _, _, _, _, obj_metadata] = obj_info
    [workspace_id, _, owner, moddate, _, _, global_permission, _, ws_metadata] = ws_info

    if obj_metadata is None:
        yield {
            '_action': 'error',
            'message': 'No object metadata for Narrative'
        }
    elif ws_metadata is None:
        yield {
            '_action': 'error',
            'message': 'No workspace metadata for Narrative'
        }
    else:
        is_temporary = _get_is_temporary(ws_metadata)

        if is_temporary is None:
            logger.error(f'No temporary metadata field for Narrative {workspace_id}')
            yield {
                '_action': 'error',
                'message': 'No temporary metadata field for Narrative'
            }
        else:
            creator = obj_data['creator']

            # however, the narratorial metadata field stores boolean as the strings "1"
            # (the "0" case is not stored)
            is_narratorial = _get_is_narratorial(ws_metadata)

            narrative_title = obj_metadata.get('name')

            # Get all the types and names of objects in the narrative's workspace.
            narrative_data_objects = indexer_utils.fetch_objects_in_workspace(workspace_id)

            raw_cells = obj_data['data'].get('cells', [])
            cells = extract_cells(raw_cells, workspace_id)

            doc = {
                '_action': 'index',
                'doc': {
                    'narrative_title': narrative_title,
                    'is_temporary': is_temporary,
                    'is_narratorial': is_narratorial,
                    'creator': creator,
                    'owner': owner,
                    'modified_at': iso8601_to_epoch(moddate),
                    'cells': cells,
                    'data_objects': narrative_data_objects,
                    'total_cells': len(cells),
                    # 'silly_extra_field': 'sillyness'
                },
                'index': _NARRATIVE_INDEX_NAME,
                'id': f'{_NAMESPACE}::{workspace_id}:{obj_id}',
            }
            yield doc


def extract_cells(cells, workspace_id):
    index_cells = []

    for cell in cells:
        if cell.get('cell_type') == 'markdown':
            if not cell.get('source'):
                # Empty markdown cell
                continue
            if cell['source'].startswith('## Welcome to KBase'):
                # Ignore boilerplate markdown cells
                continue
            # Remove all HTML and markdown formatting syntax.
            cell_soup = BeautifulSoup(_MARKDOWNER.convert(cell['source']), 'html.parser')
            index_cell = {'desc': cell_soup.get_text(), 'cell_type': "markdown"}
            index_cell['cell_type'] = "markdown"
            index_cell['desc'] = cell_soup.get_text()
        # For an app cell, the module/method name lives in metadata/kbase/appCell/app/id
        elif cell.get('cell_type') == 'code':
            index_cell = _process_code_cell(cell)
        else:
            cell_type = cell.get('cell_type', "Error: no cell type")
            sys.stderr.write(f"Narrative Indexer: could not resolve cell type \"{cell_type}\"\n")
            sys.stderr.write(str(cell))
            sys.stderr.write('\n' + ('-' * 80) + '\n')
            index_cell = {'desc': 'Narrative Cell', 'cell_type': 'unknown'}
        index_cells.append(index_cell)

    return index_cells


def _process_code_cell(cell):
    # here we want to differentiate between kbase app cells and code cells
    # app_path = get_path(cell, ['metadata', 'kbase', 'appCell', 'newAppName', 'id'])
    index_cell = {'desc': '', 'cell_type': ''}
    widget_data = get_path(cell, ['metadata', 'kbase', 'outputCell', 'widget'])
    app_cell = get_path(cell, ['metadata', 'kbase', 'appCell'])
    data_cell = get_path(cell, ['metadata', 'kbase', 'dataCell'])
    if app_cell:
        # We know that the cell is a KBase app
        # Try to get the app name from a couple possible paths in the object
        app_name1 = get_path(cell, ['metadata', 'kbase', 'attributes', 'title'])
        app_name2 = get_path(app_cell, ['app', 'id'])
        index_cell['desc'] = app_name1 or app_name2 or ''
        index_cell['cell_type'] = 'kbase_app'
    elif widget_data:
        index_cell['cell_type'] = 'widget'
        index_cell['desc'] = widget_data.get('name', '')
    elif data_cell:
        index_cell['cell_type'] = 'data'
        name = get_path(data_cell, ['objectInfo', 'name'])
        obj_type = get_path(data_cell, ['objectInfo', 'cell_type'])
        if name and obj_type:
            index_cell['desc'] = f'{name} ({obj_type})'
        else:
            index_cell['desc'] = name or obj_type or ''
    else:
        # Regular code-cell
        index_cell['cell_type'] = 'code_cell'
        index_cell['desc'] = cell.get('source', '')
    return index_cell
