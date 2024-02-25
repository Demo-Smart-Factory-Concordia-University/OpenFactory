import click
import docker
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from pyksql.ksql import KSQL

import openfactory.config as config
from openfactory.models.agents import Agent
from openfactory.models.containers import DockerContainer, EnvVar


def attach(agent_uuid):
    """ Attach a Kafka producer to an MTConnect agent """

    db_engine = create_engine(config.SQL_ALCHEMY_CONN)
    session = Session(db_engine)
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = session.execute(query).one_or_none()
    if agent is None:
        print("No agent", agent_uuid)
        return
    agent = agent[0]
    if agent.agent_container is None:
        print("Agent", agent_uuid, "has no existing container")
        return

    # Create ksqlDB table for device handeld by the agent
    ksql = KSQL(config.KSQLDB)
    ksql._statement_query(f"""CREATE TABLE IF NOT EXISTS {agent.device_uuid.replace('-', '_')} AS
                                  SELECT id,
                                         LATEST_BY_OFFSET(value) AS value
                                  FROM devices_stream
                                  WHERE device_uuid = '{agent.device_uuid}'
                                  GROUP BY id;""")

    client = docker.DockerClient(base_url=agent.node.docker_url)
    client.images.pull(config.MTCONNECT_PRODUCER_IMAGE)
    client.close()

    producer_url = agent_uuid.lower().replace("-agent", "-producer")
    container = DockerContainer(
        docker_url=agent.node.docker_url,
        image=config.MTCONNECT_PRODUCER_IMAGE,
        name=producer_url,
        environment=[
            EnvVar(variable='KAFKA_BROKER', value=config.KAFKA_BROKER),
            EnvVar(variable='KAFKA_PRODUCER_UUID', value=agent.uuid.upper().replace('-AGENT', '-PRODUCER')),
            EnvVar(variable='MTC_AGENT', value=f"{agent.agent_url}:{agent.agent_port}"),
            EnvVar(variable='MTC_AGENT_UUID', value='agent_uuid')
        ],
        network=agent.agent_container.network
    )
    session.add_all([container])
    session.commit()
    container.start()

    agent.producer_url = producer_url
    agent.producer_container = container
    session.commit()


@click.command(name='attach')
@click.argument('agent_uuid', nargs=1)
def click_attach(agent_uuid):
    """ Attach a Kafka producer to an MTConnect agent """
    attach(agent_uuid)
