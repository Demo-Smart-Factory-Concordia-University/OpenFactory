""" ofa infrastructure stack tear down command. """

import click
from openfactory.factories import remove_infrastack


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
    remove_infrastack(yaml_config_file)
