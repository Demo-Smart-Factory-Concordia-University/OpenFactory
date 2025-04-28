"""
OpenFactory utils module
"""

import glob
import os
from openfactory.config import load_yaml
from openfactory.utils.docker_compose_up import docker_compose_up
from openfactory.utils.open_uris import open_ofa
from openfactory.utils.assets import register_asset,deregister_asset

def get_nested(data, keys, default=None):
    """ Get safely a nested value from a dictionary """
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data

def find_yaml_files(folder_path, pattern='app_*.yml'):
    """ Recursively find YAML files matching a pattern in a folder and its subfolders """
    if not os.path.isdir(folder_path):
        raise ValueError(f"{folder_path} is not a valid directory.")

    search_pattern = os.path.join(folder_path, '**', pattern)
    yaml_files = sorted(glob.glob(search_pattern, recursive=True))
    return yaml_files
