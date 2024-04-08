import click
from sqlalchemy import select

from openfactory.ofa.db import db
from openfactory.models.agents import Agent


@click.command(name='stop')
@click.argument('agent_uuid', nargs=1)
def click_stop(agent_uuid):
    """ Stop an MTConnect agent defined in OpenFactory """
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = db.session.execute(query).one_or_none()
    if agent is None:
        click.echo(f'No Agent {agent_uuid} defined in OpenFactory')
        exit(1)
    else:
        agent[0].stop()
