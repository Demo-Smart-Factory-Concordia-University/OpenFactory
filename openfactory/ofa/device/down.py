import click
from openfactory.ofa.db import db
from openfactory.factories.shut_down_devices_from_config_file import shut_down_devices_from_config_file


@click.command(name='down')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def click_down(yaml_config_file):
    """ Stop and remove devices """
    shut_down_devices_from_config_file(db.session, yaml_config_file)
