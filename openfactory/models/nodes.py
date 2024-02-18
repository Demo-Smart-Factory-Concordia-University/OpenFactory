from typing import List
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from .base import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .agent import Agent


class Node(Base):
    """
    OpenFactory Node
    """

    __tablename__ = "ofa_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    node_name: Mapped[str] = mapped_column(String(20), unique=True)
    node_ip: Mapped[str] = mapped_column(String(14))
    agents: Mapped[List["Agent"]] = relationship(back_populates="node")
