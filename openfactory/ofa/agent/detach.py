from sqlalchemy import select
from sqlalchemy.orm import Session

from openfactory.models.agents import Agent


def detach(agent_uuid, db_engine):
    """ Detach a Kafka producer from an MTConnect agent """

    session = Session(db_engine)
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = session.execute(query).one_or_none()
    if agent is None:
        print("No agent", agent_uuid)
        return

    session.delete(agent[0].producer_container)
    session.commit()
