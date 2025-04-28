import click
from openfactory import OpenFactoryManager
from openfactory.ofa.ksqldb import ksql
from openfactory.ofa.utils import process_yaml_files


@click.command(name='down')
@click.argument('path', type=click.Path(exists=True), nargs=1)
@click.option('--dry-run', is_flag=True, help="Only show which YAML files would be shut down.")
def click_down(path, dry_run):
    """ Tear down devices from a YAML config file or from a folder """
    ofa = OpenFactoryManager(ksqlClient=ksql.client)
    process_yaml_files(path, dry_run,
                       action_func=ofa.shut_down_devices_from_config_file,
                       action_name="shut down",
                       pattern='dev_*.yml')
