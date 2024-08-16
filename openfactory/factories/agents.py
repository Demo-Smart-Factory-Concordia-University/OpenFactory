import os
import tempfile
from fsspec.core import split_protocol
from sqlalchemy import select

from openfactory.exceptions import OFAException
from openfactory.utils import open_ofa
from openfactory.schemas.devices import get_devices_from_config_file
from openfactory.models.user_notifications import user_notify
from openfactory.models.agents import Agent
from openfactory.models.containers import EnvVar
from openfactory.models.nodes import Node


def get_nested(data, keys, default=None):
    """ Get safely a nested value from a dictionary """
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data


def create_agents_from_config_file(db_session, yaml_config_file, run=False, attach=False):
    """
    Create MTConnect agent(s) based on a yaml configuration file
    """

    # load yaml description file
    devices = get_devices_from_config_file(yaml_config_file)
    if devices is None:
        return

    for dev_name, device in devices.items():
        user_notify.info(f"{dev_name}:")

        query = select(Agent).where(Agent.uuid == device['uuid'].upper() + '-AGENT')
        if db_session.execute(query).one_or_none() is not None:
            user_notify.info(f"Agent {device['uuid'].upper()}-AGENT exists already and was not created")
            continue

        # get node
        query = select(Node).where(Node.node_name == device['node'])
        node = db_session.execute(query).one_or_none()
        if node is None:
            raise OFAException(f"Node {device['node']} is not configured in OpenFactory")

        # get ressources if any were defined
        cpus_reservation = get_nested(device, ['agent', 'deploy', 'resources', 'reservations', 'cpus'], '0.5')
        cpus_limit = get_nested(device, ['agent', 'deploy', 'resources', 'limits', 'cpus'], '1')

        # compute device device xml uri
        device_xml_uri = device['agent']['device_xml']
        protocol, _ = split_protocol(device_xml_uri)
        if not protocol:
            if not os.path.isabs(device_xml_uri):
                device_xml_uri = os.path.join(os.path.dirname(yaml_config_file), device_xml_uri)

        # compute adapter IP
        if device['agent']['adapter']['image']:
            adapter_ip = device['uuid'].lower() + '-adapter'
        else:
            adapter_ip = device['agent']['adapter']['ip']

        # configure agent
        agent = Agent(
            uuid=device['uuid'].upper() + '-AGENT',
            external=False,
            device_xml=device_xml_uri,
            agent_port=device['agent']['port'],
            cpus_reservation=cpus_reservation,
            cpus_limit=cpus_limit,
            adapter_ip=adapter_ip,
            adapter_port=device['agent']['adapter']['port'],
            node_id=node[0].id
        )
        db_session.add_all([agent])
        db_session.commit()

        # configure adapter
        if device['agent']['adapter']['image']:
            cpus = 0 if device.get('runtime') is None else device['runtime'].get('adapter', {}).get('cpus', 0)
            env = []
            if 'environment' in device['agent']['adapter']:
                for item in device['agent']['adapter']['environment']:
                    var, val = item.split('=')
                    env.append(EnvVar(variable=var.strip(), value=val.strip()))
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
            cpus = 0 if device.get('runtime') is None else device['runtime'].get('agent', {}).get('cpus', 0)
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
            cpus = 0 if device.get('runtime') is None else device['runtime'].get('producer', {}).get('cpus', 0)
            try:
                agent.attach(cpus)
            except OFAException as err:
                user_notify.fail(f"Could not attach {device['uuid'].upper()}-AGENT\nError was: {err}")
