import click
from sqlalchemy import select

from openfactory.models.agents import Agent
from openfactory.ofa.db import db


@click.command(name='ls')
def ls():
    """ List MTConnect agents defined in OpenFactory """
    agents = select(Agent)
    print('UUID            URL             PORT     STATUS         ATTACHED')
    for agent in db.session.scalars(agents):
        print(f'{agent.uuid:15} {agent.agent_url:15} {agent.agent_port:<8d} {agent.status}        {agent.attached}')
