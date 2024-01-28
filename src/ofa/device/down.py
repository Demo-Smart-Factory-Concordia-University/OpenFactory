import yaml
import src.ofa as ofa


def down(yaml_config_file, db_engine):
    """ Stop and remove devices """

    # Load yaml description file
    with open(yaml_config_file, 'r') as stream:
        cfg = yaml.safe_load(stream)

    for dev in cfg['devices']:
        device = cfg['devices'][dev]
        ofa.agent_stop(device['UUID'].upper() + "-AGENT", db_engine)
        ofa.agent_rm(device['UUID'].upper() + "-AGENT", db_engine)
