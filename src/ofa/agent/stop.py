import docker
import requests
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.models.agents import Agent


def stop(agent_uuid, db_engine):
    """ Stop an MTConnect agent defined in OpenFactory """
    session = Session(db_engine)
    agents = select(Agent).where(Agent.uuid == agent_uuid)
    for agent in session.scalars(agents):
        if agent.external:
            print("This is an external agent. It cannot be stoped by OpenFactory")
            return
        if not agent.status == 'running':
            return
        # send agent_avail=UNAVAILABLE via MTConnect agent
        url = f"http://localhost:{agent.agent_port}/Agent"
        requests.post(url, data={'agent_avail': 'UNAVAILABLE'})
        # stop agent
        client = docker.DockerClient(base_url="ssh://" + agent.agent_url)
        container = client.containers.get(agent.container)
        container.stop()
        print("Stopped ", agent_uuid)
