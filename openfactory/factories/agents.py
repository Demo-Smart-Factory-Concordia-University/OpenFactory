import os
import docker
from fsspec.core import split_protocol
from sqlalchemy import select

from openfactory.exceptions import OFAException
from openfactory.schemas.devices import get_devices_from_config_file
from openfactory.models.user_notifications import user_notify
from openfactory.models.agents import Agent


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
        )
        db_session.add_all([agent])
        db_session.commit()

        # configure adapter
        if device['agent']['adapter']['image']:
            # get ressources if any were defined
            cpus_reservation = get_nested(device, ['agent', 'adapter', 'deploy', 'resources', 'reservations', 'cpus'], '0.5')
            cpus_limit = get_nested(device, ['agent', 'adapter', 'deploy', 'resources', 'limits', 'cpus'], '1')
            env = []
            if 'environment' in device['agent']['adapter']:
                for item in device['agent']['adapter']['environment']:
                    var, val = item.split('=')
                    env.append(f"{var.strip()}={val.strip()}")
            try:
                agent.create_adapter(device['agent']['adapter']['image'],
                                     cpus_limit=float(cpus_limit), cpus_reservation=float(cpus_reservation),
                                     environment=env)
            except docker.errors.APIError as err:
                user_notify.fail(f"Could not create {device['uuid'].lower()}-adapter\nError was: {err}")
                return

        if run:
            agent.start()
            continue

        if attach:
            try:
                agent.attach()
            except OFAException as err:
                user_notify.fail(f"Could not attach {device['uuid'].upper()}-AGENT\nError was: {err}")
