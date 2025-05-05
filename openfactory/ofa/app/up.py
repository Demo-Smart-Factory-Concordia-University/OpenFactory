""" ofa application deployment command. """

import click
from openfactory import OpenFactoryManager
from openfactory.ofa.ksqldb import ksql
from openfactory.ofa.utils import process_yaml_files


@click.command(name='up')
@click.argument('path', type=click.Path(exists=True), nargs=1)
@click.option('--dry-run', is_flag=True, help="Only show which YAML files would be deployed.")
def click_up(path: str, dry_run: bool) -> None:
    """
    Deploy OpenFactory applications from a YAML config file or a folder.

    Args:
        path (str): Path to the YAML config file or folder containing YAML files.
        dry_run (bool): If True, only show which YAML files would be deployed.
    """
    ofa = OpenFactoryManager(ksqlClient=ksql.client)
    process_yaml_files(path, dry_run,
                       action_func=ofa.deploy_apps_from_config_file,
                       action_name="deployed",
                       pattern='app_*.yml')
