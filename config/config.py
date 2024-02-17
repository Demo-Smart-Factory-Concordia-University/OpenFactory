import yaml
import os
from dotenv import load_dotenv

# load environment variables
load_dotenv('.ofaenv')

# load configuration file
with open('config/openfactory.yml', 'r') as stream:
    cfg = yaml.safe_load(stream)

# parse environment variables
for key in cfg:
    cfg[key] = os.path.expandvars(cfg[key])

# assign variables
globals().update(cfg)
