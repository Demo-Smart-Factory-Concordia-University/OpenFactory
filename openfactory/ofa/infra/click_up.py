import click
from openfactory.ofa.db import db
from .up import up


@click.command(name='up')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def click_up(yaml_config_file):
    """ Setup OpenFactory infrastructure """
    up(db.session, yaml_config_file)
