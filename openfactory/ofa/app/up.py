import click
from openfactory import OpenFactoryManager
from openfactory.ofa.ksqldb import ksql
from openfactory.ofa.utils import process_yaml_files


@click.command(name='up')
@click.argument('path', type=click.Path(exists=True), nargs=1)
@click.option('--dry-run', is_flag=True, help="Only show which YAML files would be deployed.")
def click_up(path, dry_run):
    """ Deploy OpenFactory applications from a YAML config file or from a folder """
    ofa = OpenFactoryManager(ksqlClient=ksql.client)
    process_yaml_files(path, dry_run,
                       action_func=ofa.deploy_apps_from_config_file,
                       action_name="deployed",
                       pattern='app_*.yml')
