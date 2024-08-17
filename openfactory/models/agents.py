import docker
import docker.errors
from sqlalchemy import event
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
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
from openfactory.utils import open_ofa
from openfactory.docker.swarm_manager_docker_client import swarm_manager_docker_client
from .user_notifications import user_notify
from .base import Base
from .containers import DockerContainer
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
        self.mtc_agent = f"{agent.device_uuid.lower()}-agent:5000"
        self.kafka_producer_uuid = agent.producer_uuid
        super().__init__()


class Agent(Base):
    """
    MTConnect Agent
    """

    __tablename__ = "mtc_agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(30), unique=True, doc="Agent UUID")
    external: Mapped[bool] = mapped_column(Boolean, default=False)
    device_xml: Mapped[str] = mapped_column(Text, doc="URI to device xml model")
    agent_port: Mapped[int] = mapped_column(Integer(), doc="Public port of agent")
    cpus_reservation: Mapped[int] = mapped_column(Integer(), default=0.5, doc="Minimal number of cpus required by deployed service")
    cpus_limit: Mapped[int] = mapped_column(Integer(), default=1.0, doc="Maximal number of cpus used by deployed service")
    adapter_ip: Mapped[str] = mapped_column(String(80), doc="Adapter IP")
    adapter_port: Mapped[int] = mapped_column(Integer(), doc="Adapter port")

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
    def status(self):
        """ Status of agent """
        if self.external:
            return "TO BE DONE"

        client = swarm_manager_docker_client()
        try:
            service = client.services.get(self.device_uuid.lower() + '-agent')
            tasks = service.tasks()
            return tasks[0]['Status']['State']
        except docker.errors.NotFound:
            return "stopped"
        except docker.errors.APIError as err:
            return f"docker error {err}"

    @hybrid_property
    def attached(self):
        """ Kafka producer attached or not """
        client = swarm_manager_docker_client()
        try:
            client.services.get(self.device_uuid.lower() + '-agent')
            return "yes"
        except docker.errors.NotFound:
            return "no"

    def load_device_xml(self):
        """ Loads device xml model from source based on xml model uri """
        xml_model = ""
        try:
            with open_ofa(self.device_xml) as f_remote:
                xml_model += f_remote.read()
        except (OFAException, FileNotFoundError) as err:
            user_notify.fail(f"Could not load XML device model for {self.uuid}.\n{err}")
        return xml_model

    def deploy_agent(self):
        """ Deploy agent on Docker swarm cluster """
        client = swarm_manager_docker_client()
        try:
            with open(config.MTCONNECT_AGENT_CFG_FILE, 'r') as file:
                agent_cfg = file.read()
        except FileNotFoundError:
            raise OFAException(f"Could not find the MTConnect model file '{config.MTCONNECT_AGENT_CFG_FILE}'")

        command = "sh -c 'printf \"%b\" \"$XML_MODEL\" > device.xml; printf \"%b\" \"$AGENT_CFG_FILE\" > agent.cfg; mtcagent run agent.cfg'"
        client.services.create(
            image=config.MTCONNECT_AGENT_IMAGE,
            command=command,
            name=self.device_uuid.lower() + '-agent',
            mode={"Replicated": {"Replicas": 1}},
            env=[f'MTC_AGENT_UUID={self.uuid.upper()}',
                 f'ADAPTER_UUID={self.device_uuid.upper()}',
                 f'ADAPTER_IP={self.adapter_ip}',
                 f'ADAPTER_PORT={self.adapter_port}',
                 f'XML_MODEL={self.load_device_xml()}',
                 f'AGENT_CFG_FILE={agent_cfg}'],
            endpoint_spec=docker.types.EndpointSpec(ports={self.agent_port: 5000}),
            networks=[config.OPENFACTORY_NETWORK],
            resources={
                "Limits": {"NanoCPUs": int(1000000000*self.cpus_limit)},
                "Reservations": {"NanoCPUs": int(1000000000*self.cpus_reservation)}
                }
        )

    def deploy_producer(self):
        """ Deploy Kafka producer on Docker swarm cluster """
        client = swarm_manager_docker_client()
        client.services.create(
            image=config.MTCONNECT_PRODUCER_IMAGE,
            name=self.device_uuid.lower() + '-producer',
            mode={"Replicated": {"Replicas": 1}},
            env=[f'KAFKA_BROKER={config.KAFKA_BROKER}',
                 f'KAFKA_PRODUCER_UUID={self.producer_uuid}',
                 f'MTC_AGENT={self.device_uuid.lower()}-agent:5000'],
            networks=[config.OPENFACTORY_NETWORK]
        )

    def start(self):
        """ Start agent """
        if self.external:
            user_notify.fail("This is an external agent. It cannot be started by OpenFactory")
            return
        try:
            self.deploy_agent()
            self.deploy_producer()
        except OFAException as err:
            user_notify.fail(f"Agent {self.uuid} could not be started\n{err}")
        user_notify.success(f"Agent {self.uuid} started successfully")

    def stop(self):
        """ Stop agent """
        if self.external:
            user_notify.fail("This is an external agent. It cannot be started by OpenFactory")
            return
        client = swarm_manager_docker_client()
        try:
            service = client.services.get(self.device_uuid.lower() + '-agent')
            service.remove()
            user_notify.success(f"Agent {self.uuid} stopped successfully")
        except docker.errors.NotFound:
            user_notify.info(f"Agent {self.uuid} was not running")
        except docker.errors.APIError as err:
            raise OFAException(err)
        if self.kafka_producer:
            self.kafka_producer.send_agent_availability('UNAVAILABLE')

    def attach(self):
        """ Attach a Kafka producer to the MTConnect agent """

        # create ksqlDB table for agent
        try:
            self.create_ksqldb_tables()
        except HTTPError:
            raise OFAException(f"Could not connect to ksqlDB {config.KSQLDB}")

        # create producer
        try:
            self.deploy_producer()
        except (PendingRollbackError, SSHException) as err:
            raise OFAException(f'Kafka producer for agent {self.device_uuid} could not be created. Error was: {err}')

        user_notify.success(f'Kafka producer {self.producer_uuid} started successfully')
        self.kafka_producer = AgentKafkaProducer(self)

    def detach(self):
        """ Detach agent by removing producer """
        client = swarm_manager_docker_client()
        try:
            service = client.services.get(self.device_uuid.lower() + '-producer')
            service.remove()
            user_notify.success(f"Kafka producer for agent {self.uuid} stopped successfully")
        except docker.errors.NotFound:
            user_notify.info(f"Kafka producer for agent {self.uuid} was not running")
        except docker.errors.APIError as err:
            raise OFAException(err)
        if self.kafka_producer:
            self.kafka_producer.send_producer_availability('UNAVAILABLE')

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

    def __repr__(self) -> str:
        return f"Agent (id={self.id}, uuid={self.uuid})"


@event.listens_for(Agent, 'load')
def agent_load(target, context):
    """
    Create kafka_producer if agent service is running
    """
    if target.status == 'running':
        target.kafka_producer = AgentKafkaProducer(target)


@event.listens_for(Agent, 'before_delete')
def agent_before_delete(mapper, connection, target):
    """
    Stop the various services
    """
    target.detach()
    target.stop()
