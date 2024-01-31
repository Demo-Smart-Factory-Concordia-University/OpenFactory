import docker
from sqlalchemy import select
from sqlalchemy.orm import Session

import config.config as config
from src.models.agents import Agent


def start(agent_uuid, db_engine):
    """ Start an MTConnect agent defined in OpenFactory """
    session = Session(db_engine)
    agents = select(Agent).where(Agent.uuid == agent_uuid)
    for agent in session.scalars(agents):
        if agent.external:
            print("This is an external agent. It cannot be started by OpenFactory")
            return
        client = docker.DockerClient(base_url="ssh://" + config.OPENFACTORY_USER + "@" + agent.agent_url)
        container = client.containers.get(agent.container)
        container.start()
        print("Started ", agent_uuid)
