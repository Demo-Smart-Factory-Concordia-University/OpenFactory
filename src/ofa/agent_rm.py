import docker
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.models.agents import Agent


def agent_rm(agent_uuid, db_engine):
    """ Removes an MTConnect agent defined in OpenFactory """
    session = Session(db_engine)
    agents = select(Agent).where(Agent.uuid == agent_uuid)

    for agent in session.scalars(agents):
        if not agent.external:
            if agent.status == 'running':
                print("You cannot remove a running agent. Stop it first.")
                return
            client = docker.from_env()
            container = client.containers.get(agent.agent_url)
            container.remove()
        session.delete(agent)
        print("Removed ", agent_uuid)

    session.commit()
