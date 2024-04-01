import click
import docker
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session

import openfactory.config as config
from openfactory.ofa.db import db
from openfactory.models.agents import Agent


def start(db_engine, agent_uuid):
    """ Start an MTConnect agent defined in OpenFactory """
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = session.execute(query).one_or_none()
    agent = agent[0]
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
    start(db.session, agent_uuid)
