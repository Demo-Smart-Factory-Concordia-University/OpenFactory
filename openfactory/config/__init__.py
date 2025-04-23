import yaml
import os
from dotenv import load_dotenv
from pathlib import Path
from importlib.metadata import version


def load_yaml(yaml_file):
    """
    Loads a yaml file and parses environment variables
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
