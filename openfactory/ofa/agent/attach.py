import click
import docker
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from pyksql.ksql import KSQL
from httpx import HTTPError
from paramiko.ssh_exception import SSHException
from sqlalchemy.exc import PendingRollbackError
from openfactory.exceptions import DockerComposeException
import openfactory.config as config
from openfactory.exceptions import OFAException
from openfactory.models.agents import Agent
from openfactory.models.containers import DockerContainer, EnvVar


def attach(agent_uuid, cpus=0, user_notification=print):
    """ Attach a Kafka producer to an MTConnect agent """

    db_engine = create_engine(config.SQL_ALCHEMY_CONN)
    session = Session(db_engine)
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = session.execute(query).one_or_none()
    if agent is None:
        raise OFAException(f"No agent {agent_uuid} in OpenFactory database")
    agent = agent[0]
    if agent.agent_container is None:
        raise OFAException(f"Agent {agent_uuid} has no existing container")

    # Create ksqlDB table for device handeld by the agent
    ksql = KSQL(config.KSQLDB)
    try:
        ksql._statement_query(f"""CREATE TABLE IF NOT EXISTS {agent.device_uuid.replace('-', '_')} AS
                                      SELECT id,
                                             LATEST_BY_OFFSET(value) AS value
                                      FROM devices_stream
                                      WHERE device_uuid = '{agent.device_uuid}'
                                      GROUP BY id;""")
    except HTTPError:
        raise OFAException(f"Could not connect to KSQLdb {config.KSQLDB}")
    user_notification(f"Created KSQLdb table {agent.device_uuid.replace('-', '_')}")

    # pull Docker image of producer
    try:
        client = docker.DockerClient(base_url=agent.node.docker_url)
        client.images.pull(config.MTCONNECT_PRODUCER_IMAGE)
        client.close()
    except (DockerComposeException, PendingRollbackError, SSHException) as err:
        session.rollback()
        raise OFAException(f'Docker image {config.MTCONNECT_PRODUCER_IMAGE} could not be pulled. Error was: {err}')

    # create producer
    container = DockerContainer(
        node_id=agent.node.id,
        node=agent.node,
        image=config.MTCONNECT_PRODUCER_IMAGE,
        name=agent_uuid.lower().replace("-agent", "-producer"),
        environment=[
            EnvVar(variable='KAFKA_BROKER', value=config.KAFKA_BROKER),
            EnvVar(variable='KAFKA_PRODUCER_UUID', value=agent.uuid.upper().replace('-AGENT', '-PRODUCER')),
            EnvVar(variable='MTC_AGENT', value=f"{agent.agent_url}:{agent.agent_port}"),
            EnvVar(variable='MTC_AGENT_UUID', value=f'{agent_uuid}')
        ],
        cpus=cpus
    )
    agent.producer_container = container
    try:
        session.add_all([container])
        session.commit()
    except (DockerComposeException, PendingRollbackError, SSHException) as err:
        session.rollback()
        raise OFAException(f'Producer for agent {agent_uuid} could not be created. Error was: {err}')
    user_notification(f'Producer for agent {agent_uuid} created successfully')

    # Start prodcuer
    container.start()
    user_notification(f'Producer for agent {agent_uuid} started successfully')


@click.command(name='attach')
@click.argument('agent_uuid', nargs=1)
def click_attach(agent_uuid):
    """ Attach a Kafka producer to an MTConnect agent """
    attach(agent_uuid)
