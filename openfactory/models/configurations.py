from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

import openfactory.config as config
from .base import Base


class Configuration(Base):
    """
    Configuration key-value store
    """

    __tablename__ = 'configurations'

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(20), unique=True)
    value: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)

    def __repr__(self):
        return f"{self.key} = {self.value}"


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
