import click
from openfactory.ofa.db import db
from openfactory.factories import create_agents_from_config_file


@click.command(name='up')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def up(yaml_config_file):
    """ Create and start devices """
    create_agents_from_config_file(db.session, yaml_config_file, run=True, attach=True)
