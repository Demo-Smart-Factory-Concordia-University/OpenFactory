""" OpenFactory utils module. """

import glob
import os
from typing import Dict, List, Any
from openfactory.config import load_yaml
from openfactory.utils.docker_compose_up import docker_compose_up
from openfactory.utils.open_uris import open_ofa
from openfactory.utils.assets import register_asset,deregister_asset


def get_nested(data: Dict, keys, default=None) -> Any:
    """
    Get safely a nested value from a dictionary.

    Args:
        data (dict): The dictionary to search.
        keys (list): A list of keys to traverse the dictionary.
        default: The default value to return if the key is not found.

    Returns:
        The value found at the nested key or the default value.
    """
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data


def find_yaml_files(folder_path: str, pattern='app_*.yml') -> List[str]:
    """
    Recursively find YAML files matching a pattern in a folder and its subfolders.

    Args:
        folder_path (str): The path to the folder to search in.
        pattern (str): The pattern to match files against.
    
    Returns:
        list: A list of paths to the matching YAML files.
    """
    if not os.path.isdir(folder_path):
        raise ValueError(f"{folder_path} is not a valid directory.")

    search_pattern = os.path.join(folder_path, '**', pattern)
    yaml_files = sorted(glob.glob(search_pattern, recursive=True))
    return yaml_files
