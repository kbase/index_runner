import src.utils.ws_utils as ws_utils
import logging

logger = logging.getLogger('IR')


def get_object_info(msg):
    if not msg.get('wsid') or not msg.get('objid'):
        raise RuntimeError(f'Cannot get object ref from msg: {msg}')

    obj_ref = f"{msg['wsid']}/{msg['objid']}"
    if msg.get('ver'):
        obj_ref += f"/{msg['ver']}"
    try:
        result = ws_utils.get_object_info3({
            'objects': [{'ref': obj_ref}]
        })
    except ws_utils.WorkspaceResponseError as err:
        # Workspace is deleted; ignore the error
        if (err.resp_data and isinstance(err.resp_data, dict)
                and err.resp_data['error'] and isinstance(err.resp_data['error'], dict)
                and err.resp_data['error'].get('code') == -32500):
            return
        else:
            raise err
    return result['infos'][0]


def get_object_data(msg):
    if not msg.get('wsid') or not msg.get('objid'):
        raise RuntimeError(f'Cannot get object ref from msg: {msg}')

    obj_ref = f"{msg['wsid']}/{msg['objid']}"
    if msg.get('ver'):
        obj_ref += f"/{msg['ver']}"
    try:
        response = ws_utils.get_objects2({
            'objects': [{'ref': obj_ref}]
        })
    except ws_utils.WorkspaceResponseError as err:
        # Workspace is deleted; ignore the error
        if (err.resp_data and isinstance(err.resp_data, dict)
                and err.resp_data['error'] and isinstance(err.resp_data['error'], dict)
                and err.resp_data['error'].get('code') == -32500):
            return
        else:
            raise err

    # TODO: really necessary to check the result?
    if not response or not response['data'] or not response['data'][0]:
        logger.error(response)
        raise RuntimeError("Invalid object result from the workspace")

    return response['data'][0]


def get_workspace_info(msg):
    if not msg.get('wsid'):
        raise RuntimeError(f'Cannot get workspace info from msg: {msg}')

    return ws_utils.get_workspace_info({
        'id': msg['wsid']
    })
