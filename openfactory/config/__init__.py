import yaml
import os
import json
import ast
from dotenv import load_dotenv


def load_yaml(yaml_file):
    """
    Loads a yaml file and parses environment variables
    """

    # load environment variables
    load_dotenv('.ofaenv')

    # load configuration file
    with open(yaml_file, 'r') as stream:
        cfg = yaml.safe_load(stream)

    # parse environment variables
    cfg_str = json.dumps(cfg)
    return ast.literal_eval(os.path.expandvars(cfg_str))


# assign variables
globals().update(load_yaml('openfactory/config/openfactory.yml'))
