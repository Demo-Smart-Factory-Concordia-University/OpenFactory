import click
from openfactory.factories import deploy_devices_from_config_file


@click.command(name='up')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def click_up(yaml_config_file):
    """ Deploy devices """
    deploy_devices_from_config_file(yaml_config_file)
