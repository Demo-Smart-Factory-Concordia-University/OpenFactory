""" ofa infrastructure stack setup command. """

import click
from openfactory.models.user_notifications import user_notify
from openfactory.exceptions import OFAConfigurationException, OFAException
from openfactory import OpenFactoryCluster


@click.command(name='up')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def click_up(yaml_config_file: str) -> None:
    """
    Setup OpenFactory infrastructure stack.

    Args:
        yaml_config_file (str): Path to the YAML configuration file.

    Raises:
        OFAConfigurationException: If there is an error in the configuration.
    """
    try:
        ofa = OpenFactoryCluster()
        ofa.create_infrastack_from_config_file(yaml_config_file)
    except (OFAConfigurationException, OFAException) as err:
        user_notify.fail(err)
