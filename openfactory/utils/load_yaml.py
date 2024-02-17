import yaml
import os
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
    for key in cfg:
        cfg[key] = os.path.expandvars(cfg[key])

    return cfg
