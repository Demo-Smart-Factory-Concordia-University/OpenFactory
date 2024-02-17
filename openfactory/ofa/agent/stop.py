import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from openfactory.models.agents import Agent
from openfactory.models.containers import DockerContainer


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
        url = f"http://{agent.agent_url}:{agent.agent_port}/Agent"
        requests.post(url, data={'agent_avail': 'UNAVAILABLE'})
        # stop agent
        query = select(DockerContainer).where(DockerContainer.name == agent_uuid.lower())
        agent_cont = session.execute(query).one()
        agent_cont[0].stop()
        print("Stopped", agent_uuid)
