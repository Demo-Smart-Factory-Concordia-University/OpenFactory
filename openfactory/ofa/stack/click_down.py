import click
from openfactory.ofa.db import db
from openfactory.factories import remove_infrastack


@click.command(name='down')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def click_down(yaml_config_file):
    """ Tear down OpenFactory stack """
    remove_infrastack(db.session, yaml_config_file)
