import click
from sqlalchemy import select

from openfactory.ofa.db import db
from openfactory.models.agents import Agent
from openfactory.models.user_notifications import user_notify
from openfactory.exceptions import OFAException


@click.command(name='rm')
@click.argument('agent_uuid', nargs=1)
def click_rm(agent_uuid):
    """ Remove an MTConnect agent defined in OpenFactory """
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = db.session.execute(query).one_or_none()
    if agent is None:
        user_notify.fail(f'No Agent {agent_uuid} defined in OpenFactory')
        exit(1)
    else:
        try:
            db.session.delete(agent[0])
            db.session.commit()
        except OFAException as err:
            db.session.rollback()
            user_notify.fail(f'Could not remove agent {agent_uuid}: {err}')
            exit(1)
        click.echo(f"{agent_uuid} removed successfully")
