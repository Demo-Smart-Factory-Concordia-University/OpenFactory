import click
from sqlalchemy import select
from sqlalchemy.orm import Session

from openfactory.ofa.db import db
from openfactory.models.agents import Agent


@click.command(name='detach')
@click.argument('agent_uuid', nargs=1)
def click_detach(agent_uuid):
    """ Detach a Kafka producer from an MTConnect agent """
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = db.session.execute(query).one_or_none()
    if agent is None:
        click.echo(f'No Agent {agent_uuid} defined in OpenFactory')
        exit(1)
    else:
        agent[0].detach()
        click.echo(f'Agent {agent_uuid} detached successfully')
