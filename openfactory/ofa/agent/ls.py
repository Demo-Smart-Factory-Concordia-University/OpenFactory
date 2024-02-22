import click
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session

import openfactory.config as config
from openfactory.models.agents import Agent


@click.command(name='ls')
def ls():
    """ List MTConnect agents defined in OpenFactory """
    db_engine = create_engine(config.SQL_ALCHEMY_CONN)
    session = Session(db_engine)
    agents = select(Agent)
    print('UUID            URL             PORT     STATUS         ATTACHED')
    for agent in session.scalars(agents):
        print(f'{agent.uuid:15} {agent.agent_url:15} {agent.agent_port:<8d} {agent.status}        {agent.attached}')
