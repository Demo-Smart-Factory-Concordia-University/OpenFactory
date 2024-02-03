import docker
from sqlalchemy import update
from sqlalchemy import select
from sqlalchemy.orm import Session

import config.config as config
from src.models.agents import Agent
from src.models.containers import DockerContainer


def detach(agent_uuid, db_engine):
    """ Detach a Kafka producer from an MTConnect agent """

    session = Session(db_engine)
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = session.execute(query).one_or_none()
    if agent is None:
        return
    agent = agent[0]

    client = docker.DockerClient(base_url="ssh://" + config.OPENFACTORY_USER + "@" + agent.agent_url)
    kafka_producer = client.containers.get(agent.producer_url)
    kafka_producer.stop()
    kafka_producer.remove()
    client.close()

    query = select(DockerContainer).where(DockerContainer.name == agent.producer_url)
    kafka_producer_containter = session.execute(query).one()[0]
    session.delete(kafka_producer_containter)

    query = update(Agent).where(Agent.uuid == agent_uuid).values(producer_url='')
    session.execute(query)
    session.commit()
