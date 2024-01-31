import docker
from sqlalchemy import select
from sqlalchemy.orm import Session

import config.config as config
from src.models.agents import Agent


def rm(agent_uuid, db_engine):
    """ Removes an MTConnect agent defined in OpenFactory """
    session = Session(db_engine)
    agents = select(Agent).where(Agent.uuid == agent_uuid)

    for agent in session.scalars(agents):
        if not agent.external:
            if agent.status == 'running':
                print("You cannot remove a running agent. Stop it first.")
                return
            client = docker.DockerClient(base_url="ssh://" + config.OPENFACTORY_USER + "@" + agent.agent_url)
            container = client.containers.get(agent.container)
            container.remove()
        session.delete(agent)
        print("Removed ", agent_uuid)

    session.commit()
