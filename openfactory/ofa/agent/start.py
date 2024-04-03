import click
from sqlalchemy import select
from openfactory.ofa.db import db
from openfactory.models.agents import Agent


def start(agent):
    """ Start an MTConnect agent defined in OpenFactory """
    if agent.external:
        print("This is an external agent. It cannot be started by OpenFactory")
        return
    agent.agent_container.start()
    if agent.producer_container:
        agent.producer_container.start()
        
    print("Started", agent.uuid)


@click.command(name='start')
@click.argument('agent_uuid', nargs=1)
def click_start(agent_uuid):
    """ Start an MTConnect agent defined in OpenFactory """
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = db.session.execute(query).one_or_none()
    if agent is None:
        print(f'No Agent {agent_uuid} defined in OpenFactory')
    else:
        start(agent[0])
