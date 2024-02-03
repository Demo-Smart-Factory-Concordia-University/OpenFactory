import docker
import yaml
import os
import tarfile
from tempfile import TemporaryDirectory
from sqlalchemy import select
from sqlalchemy.orm import Session

import config.config as config
import src.ofa as ofa
from src.models.agents import Agent
from src.models.containers import DockerContainer, EnvVar, Port


def _validate(device, db_engine, client):
    """ Validate that device and container do not exist """
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


def _create_agent(db_engine, device, network, docker_client, yaml_config_file):
    """ insert agent to OpenFactory data base and create Docker container of agent """

    with Session(db_engine) as session:
        agent = Agent(
            uuid=device['UUID'].upper() + '-AGENT',
            external=False,
            agent_port=device['agent']['PORT'],
            agent_url=device['NODE'],
            producer_url='',
        )

        container = DockerContainer(
            docker_url="ssh://" + config.OPENFACTORY_USER + "@" + device['NODE'],
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
            network=network,
            command='mtcagent run agent.cfg',
        )

        session.add_all([agent, container])
        session.commit()
        agent = container.create()

    # compute device file absolute path
    if os.path.isabs(device['agent']['DEVICE_XML']):
        device_file = device['agent']['DEVICE_XML']
    else:
        device_file = os.path.join(os.path.dirname(yaml_config_file), device['agent']['DEVICE_XML'])
    _copy_files(agent, device_file)
    return agent


def create(yaml_config_file, db_engine, run=False, attach=False):
    """ Create an MTConnect agent based on a yaml configuration file """

    # Load yaml description file
    with open(yaml_config_file, 'r') as stream:
        cfg = yaml.safe_load(stream)

    for dev in cfg['devices']:
        device = cfg['devices'][dev]
        client = docker.DockerClient(base_url="ssh://" + config.OPENFACTORY_USER + "@" + device['NODE'])
        if not _validate(device, db_engine, client):
            client.close()
            continue
        client.images.pull(config.MTCONNECT_AGENT_IMAGE)

        agent = _create_agent(db_engine, device, cfg['network'], client, yaml_config_file)
        print("Created", device['UUID'].upper() + "-AGENT")

        if run:
            agent.start()
            print("Started", device['UUID'].upper() + "-AGENT")

        if attach:
            ofa.agent.attach(device['UUID'].upper() + "-AGENT", db_engine)

        client.close()
