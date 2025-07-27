""" ofa infrastructure stack tear down command. """

import click
from openfactory import OpenFactoryCluster
from openfactory.models.user_notifications import user_notify
from openfactory.exceptions import OFAConfigurationException, OFAException


@click.command(name='down')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def click_down(yaml_config_file: str) -> None:
    """
    Tear down OpenFactory stack.

    Args:
        yaml_config_file (str): Path to the YAML configuration file.
    """
    try:
        ofa = OpenFactoryCluster()
        ofa.remove_infrastack_from_config_file(yaml_config_file)
    except (OFAConfigurationException, OFAException) as err:
        user_notify.fail(err)
