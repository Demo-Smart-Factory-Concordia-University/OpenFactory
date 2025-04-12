import click
from openfactory.factories import shut_down_apps_from_config_file
from openfactory.ofa.ksqldb import ksql


@click.command(name='down')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def click_down(yaml_config_file):
    """ Tear down OpenFactory applications """
    shut_down_apps_from_config_file(yaml_config_file, ksqlClient=ksql.client)
