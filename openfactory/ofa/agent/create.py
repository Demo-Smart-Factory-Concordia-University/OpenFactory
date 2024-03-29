import click
import docker
import yaml
import os
import tarfile
from tempfile import TemporaryDirectory
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

import openfactory.config as config
import openfactory.ofa as ofa
from openfactory.exceptions import OFAException
from openfactory.models.agents import Agent
from openfactory.models.nodes import Node
from openfactory.models.containers import DockerContainer, EnvVar, Port


def _validate(device, db_engine, client):
    """ Validate that device and container does not exist """
    if [cont for cont in client.containers.list() if cont.name == device['UUID'].lower() + '-agent']:
        print("A container", device['UUID'].lower() + '-agent', "exists already")
        print("Agent was not created")
        return False
    with Session(db_engine) as session:
        query = select(Agent).where(Agent.uuid == device['UUID'].upper() + '-AGENT')
        if session.execute(query).scalar():
            print("An agent with UUID", device['UUID'].upper() + '-AGENT', "exists already")
            print("Agent was not created")
            return False
    return True


def _copy_files(container, src):
    """ Copy device.xml and agent.cfg to container """

    tmp_dir = TemporaryDirectory()
    tmp_file = os.path.join(tmp_dir.name, 'files.tar')

    tar = tarfile.open(tmp_file, mode='w')
    try:
        tar.add(src, arcname='device.xml')
        tar.add(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'configs/agent.cfg'),
                arcname='agent.cfg')
    finally:
        tar.close()

    data = open(tmp_file, 'rb').read()
    container.put_archive('/home/agent', data)
    tmp_dir.cleanup()


def _create_agent(db_engine, device, yaml_config_file):
    """ Insert agent and its container to OpenFactory data base """

    with Session(db_engine) as session:

        query = select(Node).where(Node.node_name == device['NODE'])
        try:
            node = session.execute(query).one()[0]
        except NoResultFound:
            raise OFAException(f"Node {device['NODE']} is not configured in OpenFactory")

        client = docker.DockerClient(base_url=node.docker_url)
        if not _validate(device, db_engine, client):
            client.close()
            return None
        client.images.pull(config.MTCONNECT_AGENT_IMAGE)

        cpus = 0
        if 'runtime' in device:
            if 'agent' in device['runtime']:
                if 'cpus' in device['runtime']['agent']:
                    cpus = device['runtime']['agent']['cpus']

        container = DockerContainer(
            node_id=node.id,
            node=node,
            image=config.MTCONNECT_AGENT_IMAGE,
            name=device['UUID'].lower() + '-agent',
            ports=[
                Port(container_port='5000/tcp', host_port=device['agent']['PORT'])
            ],
            environment=[
                EnvVar(variable='MTC_AGENT_UUID', value=f"{device['UUID'].upper()}-AGENT"),
                EnvVar(variable='ADAPTER_UUID', value=f"{device['UUID'].upper()}"),
                EnvVar(variable='ADAPTER_IP', value=f"{device['agent']['adapter']['IP']}"),
                EnvVar(variable='ADAPTER_PORT', value=f"{device['agent']['adapter']['PORT']}"),
                EnvVar(variable='DOCKER_GATEWAY', value='172.17.0.1')
            ],
            command='mtcagent run agent.cfg',
            cpus=cpus
        )

        agent = Agent(
            uuid=device['UUID'].upper() + '-AGENT',
            external=False,
            agent_port=device['agent']['PORT'],
            node_id=node.id,
            agent_container=container
        )

        session.add_all([container, agent])
        session.commit()

        # compute device xml model absolute path
        if os.path.isabs(device['agent']['DEVICE_XML']):
            device_xml = device['agent']['DEVICE_XML']
        else:
            device_xml = os.path.join(os.path.dirname(yaml_config_file), device['agent']['DEVICE_XML'])

        # add device xml model to agent container
        cont = client.containers.get(container.name)
        _copy_files(cont, device_xml)
        client.close()
    return cont


def create(yaml_config_file, run=False, attach=False):
    """ Create an MTConnect agent based on a yaml configuration file """

    db_engine = create_engine(config.SQL_ALCHEMY_CONN)

    # Load yaml description file
    with open(yaml_config_file, 'r') as stream:
        cfg = yaml.safe_load(stream)

    for dev in cfg['devices']:
        device = cfg['devices'][dev]
        agent = _create_agent(db_engine, device, yaml_config_file)
        if agent is None:
            continue
        print("Created", device['UUID'].upper() + "-AGENT")

        if run:
            agent.start()
            print("Started", device['UUID'].upper() + "-AGENT")

        if attach:
            cpus = 0
            if 'runtime' in device:
                if 'producer' in device['runtime']:
                    if 'cpus' in device['runtime']['producer']:
                        cpus = device['runtime']['producer']['cpus']
            try:
                ofa.agent.attach(device['UUID'].upper() + "-AGENT", cpus)
                print("Attached", device['UUID'].upper() + "-AGENT")
            except OFAException as err:
                print("Could not attach", device['UUID'].upper() + "-AGENT")
                print("Error was:", err)


@click.command(name='create')
@click.argument('yaml_config_file', type=click.Path(exists=True),
                nargs=1)
def click_create(yaml_config_file):
    """ Create an MTConnect agent based on a yaml configuration file """
    create(yaml_config_file, run=False, attach=False)
