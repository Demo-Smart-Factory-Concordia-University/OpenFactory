import src.ofa as ofa


def up(yaml_config_file, db_engine):
    """ Create and start devices """
    ofa.agent.create(yaml_config_file, db_engine, run=True, attach=True)
