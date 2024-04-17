import yaml
import os
from sqlalchemy import select

from openfactory.exceptions import OFAException
from openfactory.models.user_notifications import user_notify
from openfactory.models.agents import Agent
from openfactory.models.nodes import Node


def create_agents_from_config_file(db_session, yaml_config_file, run=False, attach=False):
    """
    Create MTConnect agent(s) based on a yaml configuration file
    """

    # Load yaml description file
    with open(yaml_config_file, 'r') as stream:
        cfg = yaml.safe_load(stream)

    for dev in cfg['devices']:
        device = cfg['devices'][dev]
        print(f"{device['UUID']}:")

        query = select(Agent).where(Agent.uuid == device['UUID'].upper() + '-AGENT')
        if db_session.execute(query).one_or_none() is not None:
            user_notify.info(f"Agent {device['UUID'].upper()}-AGENT exists already and was not created")
            continue

        # get node
        query = select(Node).where(Node.node_name == device['NODE'])
        node = db_session.execute(query).one_or_none()
        if node is None:
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
            node_id=node[0].id
        )
        db_session.add_all([agent])
        db_session.commit()

        # create agent
        agent.create_container(device['agent']['adapter']['IP'],
                               device['agent']['adapter']['PORT'],
                               device_xml,
                               cpus)

        if run:
            agent.start()

        if attach:
            cpus = 0
            if 'runtime' in device:
                if 'producer' in device['runtime']:
                    if 'cpus' in device['runtime']['producer']:
                        cpus = device['runtime']['producer']['cpus']
            try:
                agent.attach(cpus)
            except OFAException as err:
                user_notify.fail(f"Could not attach {device['UUID'].upper()}-AGENT\nError was: {err}")
