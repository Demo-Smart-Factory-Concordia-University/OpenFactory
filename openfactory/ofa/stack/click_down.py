import click
from openfactory.ofa.db import db
from .down import down


@click.command(name='down')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def click_down(yaml_config_file):
    """ Tear down OpenFactory stack """
    down(db.session, yaml_config_file)
