import docker
import yaml
import os
import tarfile
from tempfile import TemporaryDirectory
from sqlalchemy.orm import Session

import config.config as config
from src.models.agents import Agent
import src.ofa as ofa


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


def _insert_agent_to_db(db_engine, cfg):
    """ insert agent to OpenFactory data base """

    with Session(db_engine) as session:
        agent = Agent(
            uuid=cfg['UUID'].upper() + '-AGENT',
            external=False,
            agent_port=cfg['agent']['PORT'],
            agent_url=cfg['NODE'],
            producer_url='',
        )
        session.add_all([agent])
        session.commit()


def create(yaml_config_file, db_engine, run=False, attach=False):
    """ Create an MTConnect agent based on a yaml configuration file """

    # Load yaml description file
    with open(yaml_config_file, 'r') as stream:
        cfg = yaml.safe_load(stream)

    for dev in cfg['devices']:
        device = cfg['devices'][dev]
        agent_cfg = device['agent']
        adapter_cfg = agent_cfg['adapter']
        client = docker.DockerClient(base_url="ssh://" + device['NODE'])
        client.images.pull(config.MTCONNECT_AGENT_IMAGE)
        network = client.networks.get(cfg['network'])
        docker_gateway = network.attrs['IPAM']['Config'][0]['Gateway']

        agent = client.containers.create(config.MTCONNECT_AGENT_IMAGE,
                                         detach=True,
                                         name=device['UUID'].lower() + '-agent',
                                         environment=[f"MTC_AGENT_UUID={device['UUID'].upper()}-AGENT",
                                                      f"ADAPTER_UUID={device['UUID'].upper()}",
                                                      f"ADAPTER_IP={adapter_cfg['IP']}",
                                                      f"ADAPTER_PORT={adapter_cfg['PORT']}",
                                                      f"DOCKER_GATEWAY={docker_gateway}"],
                                         ports={'5000/tcp': agent_cfg['PORT']},
                                         command='mtcagent run agent.cfg',
                                         network=cfg['network'])

        # compute device file absolute path
        if os.path.isabs(agent_cfg['DEVICE_XML']):
            device_file = agent_cfg['DEVICE_XML']
        else:
            device_file = os.path.join(os.path.dirname(yaml_config_file), agent_cfg['DEVICE_XML'])

        _copy_files(agent, device_file)
        _insert_agent_to_db(db_engine, device)
        print("Created", device['UUID'].upper() + "-AGENT")

        if run:
            agent.start()
            print("Started", device['UUID'].upper() + "-AGENT")

        if attach:
            ofa.agent.attach(device['UUID'].upper() + "-AGENT", db_engine)

        client.close()
