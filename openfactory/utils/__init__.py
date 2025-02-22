"""
OpenFactory utils module
"""

from ..config import load_yaml
from .docker_compose_up import docker_compose_up
from .open_uris import open_ofa
from .assets import register_asset,deregister_asset

def get_nested(data, keys, default=None):
    """ Get safely a nested value from a dictionary """
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data
