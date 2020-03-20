from src.utils.config import config
from kbase_workspace_client import WorkspaceClient
from kbase_workspace_client.exceptions import WorkspaceResponseError
import logging

logger = logging.getLogger('IR')


def get_type_pieces(type_str):
    """
    Given a full type string, returns (module, name, ver)
     - Given "KBaseNarrative.Narrative-4.0"
     - Returns ("KBaseNarrative", "Narrative", "4.0")
    """
    (full_name, type_version) = type_str.split('-')
    (type_module, type_name) = full_name.split('.')
    return (type_module, type_name, type_version)


def workspace_admin_method(method):
    return method

# The index runner originally used just the admin methods, but it ends
# up that the non-admin methods are


def __workspace_method(method):
    if method == 'listObjects':
        return 'Workspace.list_objects'
    elif method == 'getObjects':
        return 'Workspace.get_objects2'
    elif method == 'getObjectInfo':
        return 'Workspace.get_object_info3'
    elif method == 'getWorkspaceInfo':
        return 'Workspace.get_workspace_info'
    elif method == 'getPermissionsMass':
        return 'Workspace.get_permissions_mass'
    elif method == 'listWorkspaces':
        return 'Workspace.list_workspaces'
    else:
        raise ValueError(f'Workspace method "{method}" not supported    "')


def is_workspace_admin():
    # TODO: this should not be configured, rather we should make a
    # request to the workspace to see if the provided token is admin
    # and cache the result.
    return config()['ws_admin']


def list_objects(params, username=None):
    return __workspace_request('listObjects', params, username=None)


def get_objects2(params, username=None):
    return __workspace_request('getObjects', params, username=None)


def get_object_info3(params, username=None):
    return __workspace_request('getObjectInfo', params, username=None)


def get_workspace_info(params, username=None):
    return __workspace_request('getWorkspaceInfo', params, username=None)


def get_permissions_mass(params, username=None):
    return __workspace_request('getPermissionsMass', params, username=None)


def list_workspaces(params, username=None):
    return __workspace_request('listWorkspaces', params, username=None)


def __workspace_request(method, params, username=None):
    ws_client = WorkspaceClient(url=config()['kbase_endpoint'], token=config()['ws_token'])
    try:
        if is_workspace_admin():
            if username is not None:
                return ws_client.admin_req(method, params, username)
            else:
                return ws_client.admin_req(method, params)
        else:
            return ws_client.req(__workspace_method(method), params)
    except WorkspaceResponseError as err:
        logger.error('Workspace response error:', err.resp_data)
        raise err


def handle_id_to_file(handle_id, dest_path):
    """given handle id, download associated file from shock."""
    ws_client = WorkspaceClient(url=config()['kbase_endpoint'], token=config()['ws_token'])
    shock_id = ws_client.handle_to_shock(handle_id)
    ws_client.download_shock_file(shock_id, dest_path)


# NOTE: this function ripped from kbase-workspace-client
def list_workspace_ids(wsid, minid=1, maxid=None, latest=True):
    """
    Generator, yielding all object IDs + version IDs in a workspace.
    This handles the 10k pagination and will generate *all* ids.
    Args:
        wsid - int - workspace id (int)
        latest - bool - default True - Generate only the latest version of each obj.
        admin - bool - default False - Make the "list_objects" request as an admin request.
    Yields object ids
    """
    params = {"ids": [wsid]}  # type: dict
    if maxid:
        params['maxObjectID'] = maxid
    if not latest:
        params['showAllVersions'] = 1
    while True:
        params['minObjectID'] = minid
        part = __workspace_request('listObjects', params)
        if len(part) < 1:
            break
        minid = part[-1][0] + 1
        for obj in part:
            yield (obj[0], obj[4])  # yield (obj_id, obj_version)


def object_info_to_dict(obj_info):
    [id, name, ws_type, saved_date, version, saved_by,
     wsid, wsname, checksum, size, metadata] = obj_info
    return {
        'id': id,
        'name': name,
        'version': version,
        'type': ws_type,
        'saved_date': saved_date,
        'saved_by': saved_by,
        'workspace_id': wsid,
        'workspace_name': wsname,
        'checksum': checksum,
        'size': size,
        'metadata': metadata
    }


def workspace_info_to_dict(ws_info):
    [id, name, owner, moddate,
     max_objid, user_permission, global_permission,
     lockstat, metadata] = ws_info
    return {
        'id': id,
        'name': name,
        'owner': owner,
        'modification_date': moddate,
        'max_object_id': max_objid,
        'user_permission': user_permission,
        'global_permission': global_permission,
        'lock_status': lockstat,
        'metadata': metadata
    }
