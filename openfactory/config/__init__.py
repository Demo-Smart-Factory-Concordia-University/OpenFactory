""" OpenFactory configuration module. """

import yaml
import os
from dotenv import load_dotenv
from pathlib import Path
from importlib.metadata import version
from typing import Any


def load_yaml(yaml_file: str) -> Any:
    """
    Loads a YAML file and parses it, expanding environment variables.

    Reads a YAML file, expands any environment variables in the content,
    and loads the parsed data. It also sets the `OPENFACTORY_VERSION` environment variable 
    to the current version of the OpenFactory package and loads environment variables 
    from the `.ofaenv` file.

    Args:
        yaml_file (str): The path to the YAML file to be loaded.

    Returns:
        Any: The parsed YAML data, which can be of any structure depending on the file contents.
    """
    # Set the OPENFACTORY_VERSION env variable
    os.environ["OPENFACTORY_VERSION"] = f"v{version('openfactory')}"

    # Load env vars from file
    load_dotenv('.ofaenv')

    # Read raw YAML and expand env vars before parsing
    with open(yaml_file, 'r') as stream:
        raw_yaml = stream.read()
        expanded_yaml = os.path.expandvars(raw_yaml)
        return yaml.safe_load(expanded_yaml)


# assign variables
config_file = Path.joinpath(Path(__file__).resolve().parent, 'openfactory.yml')
globals().update(load_yaml(config_file))

MTCONNECT_AGENT_CFG_FILE = os.path.join(Path(__file__).resolve().parent, 'agent.cfg')
