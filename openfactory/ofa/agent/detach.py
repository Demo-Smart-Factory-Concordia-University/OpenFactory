import click
from sqlalchemy import select

from openfactory.ofa.db import db
from openfactory.models.agents import Agent
from openfactory.models.user_notifications import user_notify
from openfactory.exceptions import OFAException


@click.command(name='detach')
@click.argument('agent_uuid', nargs=1)
def click_detach(agent_uuid):
    """ Detach a Kafka producer from an MTConnect agent """
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = db.session.execute(query).one_or_none()
    if agent is None:
        user_notify.fail(f'No Agent {agent_uuid} defined in OpenFactory')
        exit(1)
    else:
        try:
            agent[0].detach()
        except OFAException as err:
            user_notify.fail(f'Could not detach agent {agent_uuid}: {err}')
            exit(1)
        click.echo(f'Agent {agent_uuid} detached successfully')
