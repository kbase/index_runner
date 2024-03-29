import pytest
import responses

from tests.helpers import set_env
from src.index_runner.main import _handle_msg, _reindex_narrative
from src.utils.config import config

# Allow requests to the service wizard (which happens in config)
responses.add_passthru(config()['service_wizard_url'])


def test_handle_msg_skip_types():
    """
    Test that an event from a type from the blacklist results in a no-op in _handle_msg
    """
    with set_env(SKIP_TYPES='xyz'):
        config(force_reload=True)
        res = _handle_msg({'objtype': 'xyz', 'evtype': 'x'})
    assert res is None


def test_handle_msg_skip_types2():
    """
    Test that an event from a type NOT in the blacklist results in _handle_msg
    trying to handle the message
    """
    with set_env(SKIP_TYPES='xyz'):
        config(force_reload=True)
        res = _handle_msg({'objtype': 'abc', 'evtype': 'x'})
    assert res is None


def test_handle_msg_allow_types():
    """
    Test that an event from a type NOT IN the whitelist results in a no-op in _handle_msg
    """
    with set_env(ALLOW_TYPES='xyz'):
        config(force_reload=True)
        res = _handle_msg({'objtype': 'abc', 'evtype': 'x'})
    assert res is None


def test_handle_msg_allow_types2():
    """
    Test that an event from a type IN the whitelist results in _handle_msg
    trying to handle the message
    """
    with set_env(ALLOW_TYPES='xyz'):
        config(force_reload=True)
        with pytest.raises(RuntimeError) as ctx:
            _handle_msg({'objtype': 'xyz'})
    assert str(ctx.value) == "Missing 'evtype' in event: {'objtype': 'xyz'}"


def test_skip_workspace():
    """
    Test that an event from a workspace in skip_workspaces is skipped.
    """
    with set_env(SKIP_WORKSPACES='123,124'):
        config(force_reload=True)
        res = _handle_msg({'objtype': 'abc', 'evtype': 'REINDEX', 'wsid': 123})
    assert res is None


def test_skip_reindex():
    """
    Test that a large workspace doesn't cause a reindex
    """
    ws_info = [123, 'auser:narrative_1653154144334',
               'auser', '2022-06-28T16:02:17+0000', 1000,
               'n', 'n', 'unlocked', {}]
    res = _reindex_narrative(None, ws_info)
    assert res is None


@responses.activate
def test_handle_msg_no_objtype():
    """Valid test path for filtering by type when no `objtype` field is
    provided, and we fetch the type from the workspace based on the object
    reference."""
    objtype = "TypeModule.TypeName-1.2"
    # Mock response
    mock_resp = {
        "version": "1.1",
        "result": [{
            "infos": [[
                1,  # objid
                "objname",
                objtype,
                "2020-08-11T23:12:28+0000",
                57,  # version
                "creator_username",
                33192,  # workspace id
                "workspace_name",
                "checksum",
                24500,  # bytes
                {},
            ]],
            "paths": [["33192/1/57"]]
        }]
    }
    responses.add(responses.POST, config()['workspace_url'], json=mock_resp)
    with set_env(SKIP_TYPES=objtype):
        config(force_reload=True)
        res = _handle_msg({'objid': 1, 'wsid': 3000, 'evtype': 'x'})
    assert res is None
