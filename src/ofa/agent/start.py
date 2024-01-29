import docker
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.models.agents import Agent


def start(agent_uuid, db_engine):
    """ Start an MTConnect agent defined in OpenFactory """
    session = Session(db_engine)
    agents = select(Agent).where(Agent.uuid == agent_uuid)
    for agent in session.scalars(agents):
        if agent.external:
            print("This is an external agent. It cannot be started by OpenFactory")
            return
        client = docker.from_env()
        container = client.containers.get(agent.agent_url)
        container.start()
        print("Started ", agent_uuid)
