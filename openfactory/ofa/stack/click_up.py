import click
import openfactory.ofa as ofa
from openfactory.ofa.db import db
from openfactory.exceptions import OFAConfigurationException
from .up import up


@click.command(name='up')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def click_up(yaml_config_file):
    """ Setup OpenFactory infrastructure stack """
    try:
        up(db.session, yaml_config_file,
           user_notification=ofa.success_msg)
    except OFAConfigurationException as err:
        ofa.fail_msg(err)
