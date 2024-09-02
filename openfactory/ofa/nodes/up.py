import click
from openfactory.models.user_notifications import user_notify
from openfactory.exceptions import OFAConfigurationException
from openfactory.factories import create_infrastack


@click.command(name='up')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def click_up(yaml_config_file):
    """ Setup OpenFactory infrastructure stack """
    try:
        create_infrastack(yaml_config_file)
    except OFAConfigurationException as err:
        user_notify.fail(err)
