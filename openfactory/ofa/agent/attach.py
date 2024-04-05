import click
from sqlalchemy import select
from httpx import HTTPError
from paramiko.ssh_exception import SSHException
from sqlalchemy.orm import Session
from sqlalchemy.exc import PendingRollbackError
from openfactory.exceptions import DockerComposeException
import openfactory.config as config
from openfactory.ofa.db import db
from openfactory.exceptions import OFAException
from openfactory.models.agents import Agent
from openfactory.models.containers import DockerContainer, EnvVar


def attach(agent, cpus=0, user_notification=print):
    """ Attach a Kafka producer to an MTConnect agent """

    if agent.agent_container is None:
        raise OFAException(f"Agent {agent.uuid} has no existing container")
    session = Session.object_session(agent)

    # Create ksqlDB table for device handeld by the agent
    try:
        agent.create_ksqldb_tables()
    except HTTPError:
        raise OFAException(f"Could not connect to KSQLdb {config.KSQLDB}")
    user_notification((f"KSQLdb tables {agent.device_uuid.replace('-', '_')}, "
                       f"{agent.uuid.upper().replace('-', '_')} and "
                       f"{agent.producer_uuid.replace('-', '_')} created successfully"))

    # create producer
    container = DockerContainer(
        node_id=agent.node.id,
        node=agent.node,
        image=config.MTCONNECT_PRODUCER_IMAGE,
        name=agent.uuid.lower().replace("-agent", "-producer"),
        environment=[
            EnvVar(variable='KAFKA_BROKER', value=config.KAFKA_BROKER),
            EnvVar(variable='KAFKA_PRODUCER_UUID', value=agent.producer_uuid),
            EnvVar(variable='MTC_AGENT', value=f"{agent.agent_url}:{agent.agent_port}"),
        ],
        cpus=cpus
    )
    agent.producer_container = container
    try:
        session.add_all([container])
        session.commit()
    except (DockerComposeException, PendingRollbackError, SSHException) as err:
        session.rollback()
        raise OFAException(f'Kafka producer for agent {agent.device_uuid} could not be created. Error was: {err}')
    user_notification(f'Kafka producer {agent.producer_uuid} created successfully')

    # Start producer
    container.start()
    user_notification(f'Kafka producer {agent.producer_uuid} started successfully')


@click.command(name='attach')
@click.argument('agent_uuid', nargs=1)
def click_attach(agent_uuid):
    """ Attach a Kafka producer to an MTConnect agent """
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = db.session.execute(query).one_or_none()
    if agent is None:
        print(f'No Agent {agent_uuid} defined in OpenFactory')
    else:
        attach(agent[0])
        print(f'Agent {agent_uuid} attached successfully')
