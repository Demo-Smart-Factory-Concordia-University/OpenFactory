import click
from sqlalchemy import select
from openfactory.ofa.db import db
from openfactory.models.agents import Agent


@click.command(name='attach')
@click.argument('agent_uuid', nargs=1)
def click_attach(agent_uuid):
    """ Attach a Kafka producer to an MTConnect agent """
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = db.session.execute(query).one_or_none()
    if agent is None:
        print(f'No Agent {agent_uuid} defined in OpenFactory')
        exit(1)
    else:
        agent[0].attach()
        print(f'Agent {agent_uuid} attached successfully')
