import yaml
import os
import tempfile
from fsspec.core import split_protocol
from sqlalchemy import select

from openfactory.exceptions import OFAException
from openfactory.utils import open_ofa
from openfactory.models.user_notifications import user_notify
from openfactory.models.agents import Agent
from openfactory.models.containers import EnvVar
from openfactory.models.nodes import Node


def create_agents_from_config_file(db_session, yaml_config_file, run=False, attach=False):
    """
    Create MTConnect agent(s) based on a yaml configuration file
    """

    # load yaml description file
    with open(yaml_config_file, 'r') as stream:
        cfg = yaml.safe_load(stream)

    for dev in cfg['devices']:
        device = cfg['devices'][dev]
        user_notify.info(f"{device['uuid']}:")

        query = select(Agent).where(Agent.uuid == device['uuid'].upper() + '-AGENT')
        if db_session.execute(query).one_or_none() is not None:
            user_notify.info(f"Agent {device['uuid'].upper()}-AGENT exists already and was not created")
            continue

        # get node
        query = select(Node).where(Node.node_name == device['node'])
        node = db_session.execute(query).one_or_none()
        if node is None:
            raise OFAException(f"Node {device['node']} is not configured in OpenFactory")

        # configure agent
        agent = Agent(
            uuid=device['uuid'].upper() + '-AGENT',
            external=False,
            agent_port=device['agent']['port'],
            node_id=node[0].id
        )
        db_session.add_all([agent])
        db_session.commit()

        # configure adapter
        if 'image' in device['agent']['adapter']:
            cpus = device.get('runtime', {}).get('adapter', {}).get('cpus', 0)
            env = []
            if 'environment' in device['agent']['adapter']:
                for var, val in device['agent']['adapter']['environment'].items():
                    env.append(EnvVar(variable=var, value=val))
            try:
                agent.create_adapter(device['agent']['adapter']['image'],
                                     cpus=cpus, environment=env)
            except OFAException as err:
                db_session.rollback()
                db_session.delete(agent)
                user_notify.fail(f"Could not create {device['uuid'].lower()}-adapter\nError was: {err}")
                db_session.commit()
                return
            agent.adapter_container.start()
            user_notify.success(f"Adapter {agent.adapter_container.name} started successfully")
            adapter_ip = agent.device_uuid.lower() + '-adapter'
        else:
            adapter_ip = device['agent']['adapter']['ip']

        # compute device xml-model absolute path
        device_xml_uri = device['agent']['device_xml']
        protocol, _ = split_protocol(device_xml_uri)
        if not protocol:
            if not os.path.isabs(device_xml_uri):
                device_xml_uri = os.path.join(os.path.dirname(yaml_config_file), device_xml_uri)

        with tempfile.TemporaryDirectory() as tmpdir:

            # copy device xml-model to a local file device_xml
            device_xml = os.path.join(tmpdir, 'device.xml')
            try:
                with open_ofa(device_xml_uri) as f_remote:
                    with open(device_xml, 'w') as f_tmp:
                        f_tmp.write(f_remote.read())
            except OFAException as err:
                db_session.delete(agent)
                user_notify.fail(f"Could not create {device['uuid'].upper()}-AGENT.\n{err}")
                db_session.commit()
                return

            # create agent
            cpus = device.get('runtime', {}).get('agent', {}).get('cpus', 0)
            try:
                agent.create_container(adapter_ip,
                                       device['agent']['adapter']['port'],
                                       device_xml,
                                       cpus)
            except OFAException as err:
                db_session.delete(agent)
                user_notify.fail(f"Could not create {device['uuid'].upper()}-AGENT\nError was: {err}")
                db_session.commit()
                return

        if run:
            agent.start()

        if attach:
            cpus = device.get('runtime', {}).get('producer', {}).get('cpus', 0)
            try:
                agent.attach(cpus)
            except OFAException as err:
                user_notify.fail(f"Could not attach {device['uuid'].upper()}-AGENT\nError was: {err}")
