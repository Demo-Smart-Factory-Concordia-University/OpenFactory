import src.ofa as ofa


def up(yaml_config_file, db_engine):
    """ Create and start devices """
    ofa.agent_create(yaml_config_file, db_engine, run=True)
