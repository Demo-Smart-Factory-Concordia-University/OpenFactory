from sqlalchemy import update
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.agents import Agent
from src.models.containers import DockerContainer


def detach(agent_uuid, db_engine):
    """ Detach a Kafka producer from an MTConnect agent """

    session = Session(db_engine)
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = session.execute(query).one_or_none()
    if agent is None:
        print("No agent", agent_uuid)
        return

    query = select(DockerContainer).where(DockerContainer.name == agent[0].producer_url)
    kafka_producer_containter = session.execute(query).one()[0]
    session.delete(kafka_producer_containter)

    query = update(Agent).where(Agent.uuid == agent_uuid).values(producer_url='')
    session.execute(query)
    session.commit()
