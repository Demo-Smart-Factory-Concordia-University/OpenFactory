import docker
from sqlalchemy import update
from sqlalchemy import select
from sqlalchemy.orm import Session

import config.config as config
from src.models.agents import Agent
from src.models.containers import DockerContainer, EnvVar


def attach(agent_uuid, db_engine):
    """ Attach a Kafka producer to an MTConnect agent """

    session = Session(db_engine)
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = session.execute(query).one_or_none()
    if agent is None:
        print("No agent", agent_uuid)
        return
    agent = agent[0]

    client = docker.DockerClient(base_url="ssh://" + config.OPENFACTORY_USER + "@" + agent.agent_url)
    client.images.pull(config.MTCONNECT_PRODUCER_IMAGE)

    # obtain network of agent container
    query = select(DockerContainer).where(DockerContainer.name == agent_uuid.lower())
    agent_cont = session.execute(query).one_or_none()
    if agent_cont is None:
        print("Agent", agent_uuid, "has no existing container")
        client.close()
        return
    agent_cont = agent_cont[0]

    producer_url = agent_uuid.lower().replace("-agent", "-producer")
    container = DockerContainer(
        docker_url="ssh://" + config.OPENFACTORY_USER + "@" + agent.agent_url,
        image=config.MTCONNECT_PRODUCER_IMAGE,
        name=producer_url,
        environment=[
            EnvVar(variable='KAFKA_BROKER', value=config.KAFKA_BROKER),
            EnvVar(variable='KAFKA_PRODUCER_UUID', value=agent.uuid.upper().replace('-AGENT', '-PRODUCER')),
            EnvVar(variable='MTC_AGENT', value=f"{agent.agent_url}:{agent.agent_port}"),
            EnvVar(variable='MTC_AGENT_UUID', value='agent_uuid')
        ],
        network=agent_cont.network
    )
    session.add_all([container])
    session.commit()
    kafka_producer = container.create()
    kafka_producer.start()

    query = update(Agent).where(Agent.uuid == agent_uuid).values(producer_url=producer_url)
    session.execute(query)
    session.commit()
    client.close()
