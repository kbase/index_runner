from src.utils.config import config
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
    assert config()["skip_workspaces"] is None

def test_reload():
    assert config()["max_object_reindex"] == 500 
    # Force reload
    print("Reload")
    config()._cfg['last_config_reload'] = 0
    os.environ["MAX_OBJECT_REINDEX"] = "1000"
    config().reload()
    assert config()["max_object_reindex"] == 1000
    
