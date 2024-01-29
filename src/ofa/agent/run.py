from .create import create


def run(yaml_config_file, db_engine):
    """ Run an MTConnect agent based on a yaml configuration file """
    create(yaml_config_file, db_engine, run=True)
