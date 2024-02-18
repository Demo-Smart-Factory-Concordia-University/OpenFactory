import click
import docker
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session

import config.config as config
from openfactory.models.agents import Agent


def start(agent_uuid):
    """ Start an MTConnect agent defined in OpenFactory """
    db_engine = create_engine(config.SQL_ALCHEMY_CONN)
    session = Session(db_engine)
    agents = select(Agent).where(Agent.uuid == agent_uuid)
    for agent in session.scalars(agents):
        if agent.external:
            print("This is an external agent. It cannot be started by OpenFactory")
            return
        client = docker.DockerClient(base_url="ssh://" + config.OPENFACTORY_USER + "@" + agent.agent_url)
        container = client.containers.get(agent.container)
        container.start()
        print("Started ", agent_uuid)


@click.command(name='start')
@click.argument('agent_uuid', nargs=1)
def click_start(agent_uuid):
    """ Start an MTConnect agent defined in OpenFactory """
    start(agent_uuid)
