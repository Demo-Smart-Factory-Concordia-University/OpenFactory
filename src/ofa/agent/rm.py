import docker
from sqlalchemy import select
from sqlalchemy.orm import Session

import config.config as config
from src.models.agents import Agent
from src.models.containers import DockerContainer


def rm(agent_uuid, db_engine):
    """ Removes an MTConnect agent defined in OpenFactory """
    session = Session(db_engine)
    query = select(Agent).where(Agent.uuid == agent_uuid)

    for agent in session.scalars(query):
        if not agent.external:
            if agent.status == 'running':
                print("You cannot remove a running agent. Stop it first.")
                return
            client = docker.DockerClient(base_url="ssh://" + config.OPENFACTORY_USER + "@" + agent.agent_url)
            container = client.containers.get(agent.container)
            container.remove()
            query = select(DockerContainer).where(DockerContainer.name == agent_uuid.lower())
            agent_cont = session.execute(query).one()
            session.delete(agent_cont[0])
        session.delete(agent)
        print("Removed ", agent_uuid)

    session.commit()
