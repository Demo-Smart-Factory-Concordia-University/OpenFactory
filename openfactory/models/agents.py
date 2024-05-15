from sqlalchemy import event
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
from sqlalchemy.exc import PendingRollbackError
from pyksql.ksql import KSQL
from httpx import HTTPError
from paramiko.ssh_exception import SSHException
from mtc2kafka.connectors import MTCSourceConnector

import openfactory.config as config
from openfactory.exceptions import OFAException
from .user_notifications import user_notify
from .base import Base
from .containers import DockerContainer, EnvVar, Port
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .nodes import Node


agent_container_table = Table(
    "agent_container_association",
    Base.metadata,
    Column('agent_id', ForeignKey('mtc_agents.id')),
    Column('container_id', ForeignKey('docker_container.id')),
)


agent_adapter_table = Table(
    "agent_adapter_association",
    Base.metadata,
    Column('agent_id', ForeignKey('mtc_agents.id')),
    Column('adapter_id', ForeignKey('docker_container.id')),
)


agent_producer_table = Table(
    "agent_producer_association",
    Base.metadata,
    Column('agent_id', ForeignKey('mtc_agents.id')),
    Column('producer_id', ForeignKey('docker_container.id')),
)


class AgentKafkaProducer(MTCSourceConnector):
    """ Kafka producer for Agent """

    bootstrap_servers = [config.KAFKA_BROKER]

    def __init__(self, agent):
        self.mtc_agent = f"{agent.agent_container.name}:5000"
        self.kafka_producer_uuid = agent.producer_uuid
        super().__init__()


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
    adapter_container: Mapped[DockerContainer] = relationship(secondary=agent_adapter_table,
                                                              cascade="all, delete-orphan",
                                                              single_parent=True)
    producer_container: Mapped[DockerContainer] = relationship(secondary=agent_producer_table,
                                                               cascade="all, delete-orphan",
                                                               single_parent=True)

    # Kafka producer used to send messages
    kafka_producer = None

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
        if self.agent_container:
            return self.agent_container.status
        else:
            return "No container"

    @hybrid_property
    def attached(self):
        """ Kafka producer attached or not """
        if self.producer_container:
            return "yes"
        else:
            return "no"

    def start(self):
        """ Start agent """
        if self.external:
            user_notify.fail("This is an external agent. It cannot be started by OpenFactory")
            return
        if self.producer_container:
            self.producer_container.start()
            user_notify.success(f"Kafka producer {self.producer_uuid} started successfully")
        self.agent_container.start()
        user_notify.success(f"Agent {self.uuid} started successfully")

    def stop(self):
        """ Stop agent """
        if self.external:
            user_notify.fail("This is an external agent. It cannot be started by OpenFactory")
            return
        if not self.status == 'running':
            return
        self.agent_container.stop()
        if self.kafka_producer:
            self.kafka_producer.send_agent_availability('UNAVAILABLE')
        user_notify.success(f"Agent {self.uuid} stopped successfully")

    def attach(self, cpus=0):
        """ Attach a Kafka producer to an MTConnect agent """
        if self.agent_container is None:
            raise OFAException(f"Agent {self.uuid} has no existing container")
        session = Session.object_session(self)

        # Create ksqlDB table for agent
        try:
            self.create_ksqldb_tables()
        except HTTPError:
            raise OFAException(f"Could not connect to ksqlDB {config.KSQLDB}")

        # create producer
        try:
            self.create_producer(cpus)
        except (PendingRollbackError, SSHException) as err:
            session.rollback()
            raise OFAException(f'Kafka producer for agent {self.device_uuid} could not be created. Error was: {err}')

        # Start producer
        self.producer_container.start()
        user_notify.success(f'Kafka producer {self.producer_uuid} started successfully')
        self.kafka_producer = AgentKafkaProducer(self)

    def detach(self):
        """ Detach agent by removing producer """
        if self.producer_container:
            self.producer_container = None
            Session.object_session(self).commit()
            if self.kafka_producer:
                self.kafka_producer.send_producer_availability('UNAVAILABLE')

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
        try:
            container.add_file(mtc_device_file, '/home/agent/device.xml')
        except FileNotFoundError:
            raise OFAException(f"Could not find the MTConnect model file '{mtc_device_file}'")
        try:
            container.add_file(config.MTCONNECT_AGENT_CFG_FILE, '/home/agent/agent.cfg')
        except FileNotFoundError:
            raise OFAException(f"Could not find the MTConnect agent configuration file '{config.MTCONNECT_AGENT_CFG_FILE}'")
        user_notify.success(f'Agent {self.uuid} created successfully')

    def create_adapter(self, adapter_image, cpus=0, environment=[]):
        """ Create Docker container for adapter """
        container = DockerContainer(
            node_id=self.node_id,
            node=self.node,
            image=adapter_image,
            name=self.device_uuid.lower() + '-adapter',
            cpus=cpus,
            environment=environment
        )
        session = Session.object_session(self)
        session.add_all([container])
        self.adapter_container = container
        session.commit()
        user_notify.success(f'Adapter {container.name} created successfully')

    def create_ksqldb_tables(self):
        """ Create ksqlDB tables related to the agent """
        ksql = KSQL(config.KSQLDB)
        ksql._statement_query(f"""CREATE TABLE IF NOT EXISTS {self.device_uuid.replace('-', '_')} AS
                                      SELECT id,
                                             LATEST_BY_OFFSET(value) AS value
                                      FROM devices_stream
                                      WHERE device_uuid = '{self.device_uuid}'
                                      GROUP BY id;""")
        ksql._statement_query(f"""CREATE TABLE IF NOT EXISTS {self.uuid.upper().replace('-', '_')} AS
                                      SELECT id,
                                             LATEST_BY_OFFSET(value) AS value
                                      FROM devices_stream
                                      WHERE device_uuid = '{self.uuid}'
                                      GROUP BY id;""")
        ksql._statement_query(f"""CREATE TABLE IF NOT EXISTS {self.producer_uuid.replace('-', '_')} AS
                                      SELECT id,
                                             LATEST_BY_OFFSET(value) AS value
                                      FROM devices_stream
                                      WHERE device_uuid = '{self.producer_uuid}'
                                      GROUP BY id;""")
        user_notify.success((f"ksqlDB tables {self.device_uuid.replace('-', '_')}, "
                             f"{self.uuid.upper().replace('-', '_')} and "
                             f"{self.producer_uuid.replace('-', '_')} created successfully"))

    def create_producer(self, cpus=0):
        """ Create Kafka producer for agent """
        container = DockerContainer(
            node_id=self.node.id,
            node=self.node,
            image=config.MTCONNECT_PRODUCER_IMAGE,
            name=self.uuid.lower().replace("-agent", "-producer"),
            environment=[
                EnvVar(variable='KAFKA_BROKER', value=config.KAFKA_BROKER),
                EnvVar(variable='KAFKA_PRODUCER_UUID', value=self.producer_uuid),
                EnvVar(variable='MTC_AGENT', value=f"{self.agent_container.name}:5000"),
            ],
            cpus=cpus
        )
        session = Session.object_session(self)
        session.add_all([container])
        self.producer_container = container
        session.commit()
        user_notify.success(f'Kafka producer {self.producer_uuid} created successfully')

    def __repr__(self) -> str:
        return f"Agent (id={self.id}, uuid={self.uuid})"


@event.listens_for(Agent, 'load')
def agent_load(target, context):
    """
    Create kafka_producer if an agent is running
    """
    if target.agent_container:
        if target.agent_container.status == 'running':
            target.kafka_producer = AgentKafkaProducer(target)


@event.listens_for(Agent, 'after_delete')
def agent_after_delete(mapper, connection, target):
    """
    Detach agent
    """
    if target.producer_container:
        if target.kafka_producer:
            target.kafka_producer.send_producer_availability('UNAVAILABLE')

    if target.kafka_producer:
        target.kafka_producer.send_agent_availability('UNAVAILABLE')
