import docker
import docker.errors
from sqlalchemy import event
from sqlalchemy import Boolean
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import JSON
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.exc import PendingRollbackError
from pyksql.ksql import KSQL
from httpx import HTTPError
from paramiko.ssh_exception import SSHException
from mtc2kafka.connectors import MTCSourceConnector

from openfactory.docker.docker_access_layer import dal
import openfactory.config as config
from openfactory.exceptions import OFAException
from openfactory.utils import open_ofa
from .user_notifications import user_notify
from .base import Base


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
    constraints: Mapped[dict] = mapped_column(JSON, default=[], doc="Placement constraints")

    # Kafka producer used to send messages
    kafka_producer = None

    @hybrid_property
    def top_task(self):
        """
        Get the task at the top of the hierarchy
        """
        client = dal.docker_client
        try:
            service = client.services.get(self.device_uuid.lower() + '-agent')
        except docker.errors.NotFound:
            return None

        tasks = service.tasks()

        # Sort tasks by Slot number and creation time (most recent first)
        tasks.sort(key=lambda x: (x['Slot'], x['CreatedAt']), reverse=True)

        latest_tasks = {}

        for task in tasks:
            task_slot = task['Slot']
            node_id = task['NodeID']

            # Use a combination of Slot and NodeID as the unique key
            slot_node_key = (task_slot, node_id)

            # Store only the latest task for each Slot/Node combination
            if slot_node_key not in latest_tasks:
                latest_tasks[slot_node_key] = task

        # Find the task that is the most recent in its Slot/NodeID
        if latest_tasks:
            top_task = max(latest_tasks.values(), key=lambda x: x['CreatedAt'])
            return top_task

        return None

    @hybrid_property
    def node(self):
        """ Swarm node where agent is deployed """
        if self.external:
            return "TO BE DONE"

        client = dal.docker_client
        try:
            node = client.nodes.get(self.top_task['NodeID'])
            return f"{node.attrs['Description']['Hostname']} ({node.attrs['Status']['Addr']})"
        except docker.errors.NotFound:
            return "none"
        except docker.errors.APIError as err:
            return f"docker error {err}"

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

        try:
            task = self.top_task
        except docker.errors.APIError as err:
            return f"docker error {err}"
        if task:
            return task['Status']['State']
        else:
            return "stopped"

    @hybrid_property
    def attached(self):
        """ Kafka producer attached or not """
        client = dal.docker_client
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
        client = dal.docker_client
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
                },
            constraints=self.constraints
        )

    def deploy_producer(self):
        """ Deploy Kafka producer on Docker swarm cluster """
        client = dal.docker_client
        client.services.create(
            image=config.MTCONNECT_PRODUCER_IMAGE,
            name=self.device_uuid.lower() + '-producer',
            mode={"Replicated": {"Replicas": 1}},
            env=[f'KAFKA_BROKER={config.KAFKA_BROKER}',
                 f'KAFKA_PRODUCER_UUID={self.producer_uuid}',
                 f'MTC_AGENT={self.device_uuid.lower()}-agent:5000'],
            constraints=self.constraints,
            networks=[config.OPENFACTORY_NETWORK]
        )

    def start(self):
        """ Start agent """
        if self.external:
            user_notify.fail("This is an external agent. It cannot be started by OpenFactory")
            return
        try:
            self.deploy_agent()
            self.attach()
        except OFAException as err:
            user_notify.fail(f"Agent {self.uuid} could not be started\n{err}")
        user_notify.success(f"Agent {self.uuid} started successfully")

    def stop(self):
        """ Stop agent """
        if self.external:
            user_notify.fail("This is an external agent. It cannot be started by OpenFactory")
            return
        client = dal.docker_client
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
        client = dal.docker_client
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

    def create_adapter(self, adapter_image, cpus_limit=1, cpus_reservation=0.5, environment=[]):
        """ Create Docker container for adapter """
        client = dal.docker_client
        client.services.create(
            image=adapter_image,
            name=self.device_uuid.lower() + '-adapter',
            mode={"Replicated": {"Replicas": 1}},
            env=environment,
            networks=[config.OPENFACTORY_NETWORK],
            resources={
                "Limits": {"NanoCPUs": int(1000000000*cpus_limit)},
                "Reservations": {"NanoCPUs": int(1000000000*cpus_reservation)}
                }
        )
        user_notify.success(f"Adapter {self.device_uuid.lower() + '-adapter'} created successfully")

    def remove_adapter(self):
        """ Removes adapter if it is a Docker swarm service """
        client = dal.docker_client
        try:
            service = client.services.get(self.device_uuid.lower() + '-adapter')
            service.remove()
            user_notify.success(f"Adapter for agent {self.uuid} removed successfully")
        except docker.errors.NotFound:
            # no adapter running as a Docker swarm service
            pass
        except docker.errors.APIError as err:
            raise OFAException(err)

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
    target.remove_adapter()
    target.detach()
    target.stop()
