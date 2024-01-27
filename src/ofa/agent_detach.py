import docker
from sqlalchemy import update
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.models.agents import Agent


def agent_detach(agent_uuid, db_engine):
    """ Detach a Kafka producer from an MTConnect agent """

    session = Session(db_engine)
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = session.execute(query).one()[0]

    client = docker.from_env()
    kafka_producer = client.containers.get(agent.producer_url)
    kafka_producer.stop()
    kafka_producer.remove()

    query = update(Agent).where(Agent.uuid == agent_uuid).values(producer_url='')
    session.execute(query)
    session.commit()
