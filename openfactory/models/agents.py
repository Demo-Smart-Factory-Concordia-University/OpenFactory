import docker
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Session
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

import openfactory.config as config
from .base import Base
from .containers import DockerContainer, EnvVar, Port
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
    uuid: Mapped[str] = mapped_column(String(30), unique=True)
    external = mapped_column(Boolean, default=False)
    agent_port = mapped_column(Integer())
    node_id = mapped_column(ForeignKey("ofa_nodes.id"))
    node: Mapped["Node"] = relationship(back_populates="agents")
    agent_container: Mapped[DockerContainer] = relationship(secondary=agent_container_table,
                                                            cascade="all, delete-orphan",
                                                            single_parent=True)
    producer_container: Mapped[DockerContainer] = relationship(secondary=agent_producer_table,
                                                               cascade="all, delete-orphan",
                                                               single_parent=True)

    @hybrid_property
    def agent_url(self):
        """ URL of node where agent is running """
        return self.node.node_ip

    @hybrid_property
    def device_uuid(self):
        """ Device UUID handeld by agent """
        return self.uuid.upper().replace('-AGENT', '')

    @hybrid_property
    def producer_uuid(self):
        """ Kafka producer UUID for the agent """
        return self.uuid.upper().replace('-AGENT', '-PRODUCER')

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
        client = docker.DockerClient(base_url=self.agent_container.docker_url)
        container = client.containers.get(self.uuid.lower())
        return container.attrs['State']['Status']

    @hybrid_property
    def attached(self):
        """ Kafka producer attached or not """
        if self.producer_container:
            return "yes"
        else:
            return "no"

    def create_container(self, adapter_ip, adapter_port, mtc_device_file, cpus=0):
        """ Create Docker container for agent """
        container = DockerContainer(
            node_id=self.node_id,
            node=self.node,
            image=config.MTCONNECT_AGENT_IMAGE,
            name=self.device_uuid.lower() + '-agent',
            ports=[
                Port(container_port='5000/tcp', host_port=self.agent_port)
            ],
            environment=[
                EnvVar(variable='MTC_AGENT_UUID', value=self.uuid.upper()),
                EnvVar(variable='ADAPTER_UUID', value=self.device_uuid.upper()),
                EnvVar(variable='ADAPTER_IP', value=adapter_ip),
                EnvVar(variable='ADAPTER_PORT', value=adapter_port),
                EnvVar(variable='DOCKER_GATEWAY', value='172.18.0.1')
            ],
            command='mtcagent run agent.cfg',
            cpus=cpus
        )
        session = Session.object_session(self)
        session.add_all([container])
        self.agent_container = container
        session.commit()
        container.add_file(mtc_device_file, '/home/agent/device.xml')
        container.add_file(config.MTCONNECT_AGENT_CFG_FILE, '/home/agent/agent.cfg')

    def __repr__(self) -> str:
        return f"Agent (id={self.id}, uuid={self.uuid})"
