import click
from sqlalchemy import select
from sqlalchemy.orm import Session

from openfactory.ofa.db import db
from openfactory.models.agents import Agent


def detach(agent, user_notification=print):
    """ Detach a Kafka producer from an MTConnect agent """
    session = Session.object_session(agent)
    dev_uuid = agent.device_uuid
    if agent.producer_container:
        session.delete(agent.producer_container)
        session.commit()
        session.close()
        user_notification(f"Producer for {dev_uuid} removed successfully")


@click.command(name='detach')
@click.argument('agent_uuid', nargs=1)
def click_detach(agent_uuid):
    """ Detach a Kafka producer from an MTConnect agent """
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = db.session.execute(query).one_or_none()
    if agent is None:
        print(f'No Agent {agent_uuid} defined in OpenFactory')
    else:
        detach(agent[0])
        print(f'Agent {agent_uuid} detached successfully')
