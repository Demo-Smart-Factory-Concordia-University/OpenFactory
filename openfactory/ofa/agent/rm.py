import click
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session

import openfactory.config as config
from openfactory.models.agents import Agent


def rm(agent_uuid):
    """ Removes an MTConnect agent defined in OpenFactory """
    db_engine = create_engine(config.SQL_ALCHEMY_CONN)
    session = Session(db_engine)
    query = select(Agent).where(Agent.uuid == agent_uuid)

    for agent in session.scalars(query):
        if not agent.external:
            if agent.status == 'running':
                print("You cannot remove a running agent. Stop it first.")
                return
        session.delete(agent)
        session.commit()
        print("Removed", agent_uuid)


@click.command(name='rm')
@click.argument('agent_uuid', nargs=1)
def click_rm(agent_uuid):
    """ Removes an MTConnect agent defined in OpenFactory """
    rm(agent_uuid)
