import click
import yaml
import os
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

import openfactory.config as config
import openfactory.ofa as ofa
from openfactory.exceptions import OFAException
from openfactory.models.agents import Agent
from openfactory.models.nodes import Node


def _validate(device, db_session):
    query = select(Agent).where(Agent.uuid == device['UUID'].upper() + '-AGENT')
    if db_session.execute(query).scalar():
        print("An agent with UUID", device['UUID'].upper() + '-AGENT', "exists already")
        print("Agent was not created")
        return False
    return True


def create_from_config_file(yaml_config_file, run=False, attach=False):
    """ Create MTConnect agent(s) based on a yaml configuration file """

    db_engine = create_engine(config.SQL_ALCHEMY_CONN)
    db_session = Session(db_engine)

    # Load yaml description file
    with open(yaml_config_file, 'r') as stream:
        cfg = yaml.safe_load(stream)

    for dev in cfg['devices']:
        device = cfg['devices'][dev]

        if not _validate(device, db_session):
            continue

        # get node
        query = select(Node).where(Node.node_name == device['NODE'])
        try:
            node = db_session.execute(query).one()[0]
        except NoResultFound:
            raise OFAException(f"Node {device['NODE']} is not configured in OpenFactory")

        # compute device xml-model absolute path
        if os.path.isabs(device['agent']['DEVICE_XML']):
            device_xml = device['agent']['DEVICE_XML']
        else:
            device_xml = os.path.join(os.path.dirname(yaml_config_file), device['agent']['DEVICE_XML'])

        # get number of cpus
        cpus = 0
        if 'runtime' in device:
            if 'agent' in device['runtime']:
                if 'cpus' in device['runtime']['agent']:
                    cpus = device['runtime']['agent']['cpus']

        # configure agent
        agent = Agent(
            uuid=device['UUID'].upper() + '-AGENT',
            external=False,
            agent_port=device['agent']['PORT'],
            node_id=node.id
        )
        db_session.add_all([agent])
        db_session.commit()

        # create agent
        agent.create_container(device['agent']['adapter']['IP'],
                               device['agent']['adapter']['PORT'],
                               device_xml,
                               cpus)
        print(f"Agent {agent.uuid} created successfully")

        if run:
            ofa.agent.start(agent)

        if attach:
            cpus = 0
            if 'runtime' in device:
                if 'producer' in device['runtime']:
                    if 'cpus' in device['runtime']['producer']:
                        cpus = device['runtime']['producer']['cpus']
            try:
                ofa.agent.attach(agent, cpus)
            except OFAException as err:
                print("Could not attach", device['UUID'].upper() + "-AGENT")
                print("Error was:", err)


@click.command(name='create')
@click.argument('yaml_config_file', type=click.Path(exists=True),
                nargs=1)
def click_create(yaml_config_file):
    """ Create an MTConnect agent based on a yaml configuration file """
    create_from_config_file(yaml_config_file, run=False, attach=False)
