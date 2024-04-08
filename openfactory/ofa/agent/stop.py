import click
import requests
from sqlalchemy import select

from openfactory.ofa.db import db
from openfactory.models.agents import Agent


def stop(agent, user_notification=print):
    """ Stop an MTConnect agent defined in OpenFactory """
    if agent.external:
        user_notification("This is an external agent. It cannot be stoped by OpenFactory")
        return
    if not agent.status == 'running':
        return

    # send agent_avail=UNAVAILABLE via MTConnect agent
    url = f"http://{agent.agent_url}:{agent.agent_port}/Agent"
    requests.post(url, data={'agent_avail': 'UNAVAILABLE'})

    # stop agent
    agent.agent_container.stop()
    user_notification(f"{agent.uuid} stopped successfully")


@click.command(name='stop')
@click.argument('agent_uuid', nargs=1)
def click_stop(agent_uuid):
    """ Stop an MTConnect agent defined in OpenFactory """
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = db.session.execute(query).one_or_none()
    if agent is None:
        print(f'No Agent {agent_uuid} defined in OpenFactory')
    else:
        agent[0].stop()
