from src.utils.config import config
from tests.helpers import set_env
import os

"""
Add some minimal tests for the config object.
More should be added to this.
"""


def test_config_defaults():
    if "WORKSPACE_TOKEN" not in os.environ:
        os.environ["WORKSPACE_TOKEN"] = "bogus"
    if "RE_API_TOKEN" not in os.environ:
        os.environ["RE_API_TOKEN"] = "bogus"
    assert config()["max_object_reindex"] == 500
    assert config()["skip_workspaces"] == set()


def test_max_object_reindex():
    assert config()["max_object_reindex"] == 500
    # Force reload
    with set_env(MAX_OBJECT_REINDEX="1000"):
        config()._cfg['last_config_reload'] = 0
        config().reload()
    assert config()["max_object_reindex"] == 1000


def test_skip_es():
    assert config()["skip_es"] is None
    # Force reload
    with set_env(SKIP_ES='1'):
        config()._cfg['last_config_reload'] = 0
        config().reload()
    assert config()["skip_es"] == "1"
