import click
from openfactory import OpenFactoryManager
from openfactory.ofa.ksqldb import ksql


@click.command(name='up')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def click_up(yaml_config_file):
    """ Deploy OpenFactory applications """
    ofa = OpenFactoryManager(ksqlClient=ksql.client)
    ofa.deploy_apps_from_config_file(yaml_config_file)
