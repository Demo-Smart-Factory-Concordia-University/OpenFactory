import click
from sqlalchemy import select

from openfactory.models.agents import Agent
from openfactory.ofa.db import db


@click.command(name='ls')
def ls():
    """ List MTConnect agents defined in OpenFactory """
    agents = select(Agent)
    print('UUID                      NODE                      PORT     STATUS')
    for agent in db.session.scalars(agents):
        print(f'{agent.uuid:25} {agent.node:25} {agent.agent_port:<8d} {agent.status:7}')
