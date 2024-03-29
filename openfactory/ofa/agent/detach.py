import click
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session

import openfactory.config as config
from openfactory.models.agents import Agent


def detach(agent_uuid):
    """ Detach a Kafka producer from an MTConnect agent """

    db_engine = create_engine(config.SQL_ALCHEMY_CONN)
    session = Session(db_engine)
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = session.execute(query).one_or_none()
    if agent is None:
        print(f"No agent {agent_uuid} running.")
        return

    if agent[0].producer_container:
        session.delete(agent[0].producer_container)
        session.commit()
        session.close()


@click.command(name='detach')
@click.argument('agent_uuid', nargs=1)
def click_detach(agent_uuid):
    """ Detach a Kafka producer from an MTConnect agent """
    detach(agent_uuid)
