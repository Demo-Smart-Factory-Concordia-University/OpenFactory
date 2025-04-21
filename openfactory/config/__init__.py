import yaml
import os
import json
import ast
from dotenv import load_dotenv
from pathlib import Path


def load_yaml(yaml_file):
    """
    Loads a yaml file and parses environment variables
    """

    # Read the OpenFactory version from openfactory-version.txt
    with open("openfactory-version.txt", "r") as f:
        version = f.read().strip()
    os.environ["OPENFACTORY_VERSION"] = version

    # load environment variables from working directory
    load_dotenv('.ofaenv')

    # load configuration file
    with open(yaml_file, 'r') as stream:
        cfg = yaml.safe_load(stream)

    # parse environment variables
    cfg_str = json.dumps(cfg)
    return ast.literal_eval(os.path.expandvars(cfg_str))


# assign variables
config_file = Path.joinpath(Path(__file__).resolve().parent, 'openfactory.yml')
globals().update(load_yaml(config_file))
