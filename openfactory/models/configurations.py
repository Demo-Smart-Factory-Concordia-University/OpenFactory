from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

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
