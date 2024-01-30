import yaml
import src.ofa as ofa


def down(yaml_config_file, db_engine):
    """ Stop and remove devices """

    # Load yaml description file
    with open(yaml_config_file, 'r') as stream:
        cfg = yaml.safe_load(stream)

    for dev in cfg['devices']:
        device = cfg['devices'][dev]
        agent_uuid = device['UUID'].upper() + "-AGENT"
        ofa.agent.stop(agent_uuid, db_engine)
        ofa.agent.detach(agent_uuid, db_engine)
        ofa.agent.rm(agent_uuid, db_engine)
