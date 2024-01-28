from .agent_create import agent_create


def agent_run(yaml_config_file, db_engine):
    """ Run an MTConnect agent based on a yaml configuration file """
    agent_create(yaml_config_file, db_engine, run=True)
