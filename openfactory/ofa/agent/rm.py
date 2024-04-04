import click
from sqlalchemy import select
from sqlalchemy.orm import Session

import openfactory.ofa as ofa
from openfactory.ofa.db import db
from openfactory.models.agents import Agent


def rm(agent, user_notification=print):
    """ Remove an MTConnect agent defined in OpenFactory """
    agent_uuid = agent.uuid
    session = Session.object_session(agent)

    ofa.agent.detach(agent, user_notification)
    session.delete(agent)
    session.commit()
    user_notification(f"{agent_uuid} removed successfully")


@click.command(name='rm')
@click.argument('agent_uuid', nargs=1)
def click_rm(agent_uuid):
    """ Remove an MTConnect agent defined in OpenFactory """
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = db.session.execute(query).one_or_none()
    if agent is None:
        print(f'No Agent {agent_uuid} defined in OpenFactory')
    else:
        rm(agent[0])
