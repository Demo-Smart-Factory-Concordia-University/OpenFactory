from typing import List
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from .base import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .node import Node


class InfraStack(Base):
    """
    OpenFactory Infrastructure Stack
    """

    __tablename__ = "ofa_infra_stack"

    id: Mapped[int] = mapped_column(primary_key=True)
    stack_name: Mapped[str] = mapped_column(String(20), unique=True)

    nodes: Mapped[List["Node"]] = relationship(back_populates="stack")

    def __repr__(self):
        return self.stack_name

    @hybrid_property
    def manager(self):
        """ Returns swarm manager of the stack """
        if not self.nodes:
            return None
        return self.nodes[0].manager
