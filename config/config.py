import yaml
import os

# load configuration file
with open('config/openfactory.yml', 'r') as stream:
    cfg = yaml.safe_load(stream)

# parse environment variables
for key in cfg:
    cfg[key] = os.path.expandvars(cfg[key])

# assign variables
globals().update(cfg)
