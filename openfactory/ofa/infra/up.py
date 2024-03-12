import click
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import openfactory.config as config
from openfactory.core import create_infra_stack


@click.command(name='up')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def up(yaml_config_file):
    """ Setup OpenFactory infrastructure """

    db_engine = create_engine(config.SQL_ALCHEMY_CONN)
    session = Session(db_engine)
    create_infra_stack(session, yaml_config_file)
    session.close()
