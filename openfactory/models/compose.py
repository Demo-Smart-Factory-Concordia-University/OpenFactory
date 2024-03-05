from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from .base import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .node import Node


class ComposeProject(Base):
    """
    Docker compose project
    """

    __tablename__ = 'compose_projects'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)
    description: Mapped[str] = mapped_column(String(80))
    yaml_config: Mapped[str] = mapped_column(Text)
    node_id = mapped_column(ForeignKey("ofa_nodes.id"))
    node: Mapped["Node"] = relationship(back_populates="compose_projects")

    def __repr__(self):
        return self.name
