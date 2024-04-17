import click
from openfactory.ofa.db import db
from openfactory.factories import create_agents_from_config_file


@click.command(name='run')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def run(yaml_config_file):
    """ Run an MTConnect agent based on a yaml configuration file """
    create_agents_from_config_file(db.session, yaml_config_file, run=True, attach=False)
