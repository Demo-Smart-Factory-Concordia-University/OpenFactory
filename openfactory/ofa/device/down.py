import click
import yaml
from sqlalchemy import select

import openfactory.ofa as ofa
from openfactory.ofa.db import db
from openfactory.models.agents import Agent


@click.command(name='down')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def down(yaml_config_file):
    """ Stop and remove devices """

    # Load yaml description file
    with open(yaml_config_file, 'r') as stream:
        cfg = yaml.safe_load(stream)

    for dev in cfg['devices']:
        device = cfg['devices'][dev]
        agent_uuid = device['UUID'].upper() + "-AGENT"
        query = select(Agent).where(Agent.uuid == agent_uuid)
        agent = db.session.execute(query).one_or_none()
        if agent is None:
            print(f'No Agent {agent_uuid} defined in OpenFactory')
            continue
        ofa.agent.stop(agent[0])
        ofa.agent.detach(agent[0])
        ofa.agent.rm(agent_uuid)
