import docker
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from .base import Base
from .containers import DockerContainer
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .node import Node


agent_container_table = Table(
    "agent_container_association",
    Base.metadata,
    Column('agent_id', ForeignKey('mtc_agents.id')),
    Column('container_id', ForeignKey('docker_container.id')),
)


agent_producer_table = Table(
    "agent_producer_association",
    Base.metadata,
    Column('agent_id', ForeignKey('mtc_agents.id')),
    Column('producer_id', ForeignKey('docker_container.id')),
)


class Agent(Base):
    """
    MTConnect Agent
    """

    __tablename__ = "mtc_agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(30))
    external = mapped_column(Boolean, default=False)
    agent_port = mapped_column(Integer())
    node_id = mapped_column(ForeignKey("ofa_nodes.id"))
    node: Mapped["Node"] = relationship(back_populates="agents")
    agent_container: Mapped[DockerContainer] = relationship(secondary=agent_container_table)
    producer_container: Mapped[DockerContainer] = relationship(secondary=agent_producer_table)

    @hybrid_property
    def agent_url(self):
        """ URL of node where agent is running """
        return self.node.node_ip

    @hybrid_property
    def device_uuid(self):
        """ Device UUID handeld by agent """
        return self.uuid.upper().replace('-AGENT', '')

    @hybrid_property
    def container(self):
        """ Container of agent """
        if self.external:
            return ""
        return self.uuid.lower()

    @hybrid_property
    def status(self):
        """ Status of agent """
        if self.external:
            return "TO BE DONE"
        client = docker.DockerClient(base_url="ssh://" + self.agent_url)
        container = client.containers.get(self.uuid.lower())
        return container.attrs['State']['Status']

    @hybrid_property
    def attached(self):
        """ kafka producer attached or not """
        if self.producer_container:
            return "yes"
        else:
            return "no"

    def __repr__(self) -> str:
        return f"Agent (id={self.id!r}, uuid={self.uuid!r}, agent_url={self.agent_url!r})"
