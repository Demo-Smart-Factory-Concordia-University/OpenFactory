from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.agents import Agent


def rm(agent_uuid, db_engine):
    """ Removes an MTConnect agent defined in OpenFactory """
    session = Session(db_engine)
    query = select(Agent).where(Agent.uuid == agent_uuid)

    for agent in session.scalars(query):
        if not agent.external:
            if agent.status == 'running':
                print("You cannot remove a running agent. Stop it first.")
                return
            session.delete(agent.agent_container)
        session.delete(agent)
        print("Removed", agent_uuid)

    session.commit()
