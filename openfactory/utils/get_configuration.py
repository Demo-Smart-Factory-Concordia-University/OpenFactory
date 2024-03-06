from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session

from openfactory.models.configurations import Configuration
import openfactory.config as config


def get_configuration(key):
    """ Fetch configuration from database """
    db_engine = create_engine(config.SQL_ALCHEMY_CONN)
    with Session(db_engine) as session:
        query = select(Configuration).where(Configuration.key == key)
        config_var = session.execute(query).one_or_none()
    if config_var is None:
        return None
    else:
        return config_var[0].value
