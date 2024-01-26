import docker
import yaml
import os
import tarfile
from tempfile import TemporaryDirectory
from sqlalchemy.orm import Session

from src.models.agents import Agent


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


def _insert_agent_to_db(db_engine, uuid):
    """ insert agent to OpenFact data base """

    with Session(db_engine) as session:
        agent = Agent(
            uuid=uuid.upper() + '-AGENT',
            external=False,
            agent_url=uuid.lower() + '-agent',
            producer_url='',
        )
        session.add_all([agent])
        session.commit()


def agent_create(yaml_config_file, db_engine):
    """ Create an MTConnect agent based on a yaml configuration file """

    # Load yaml description file
    with open(yaml_config_file, 'r') as stream:
        cfg = yaml.safe_load(stream)

    agent_cfg = cfg['agent']
    adapter_cfg = cfg['adapter']

    client = docker.from_env()

    # create agent container
    agent = client.containers.create("rwuthric/mtcagent",
                                     detach=True,
                                     name=cfg['UUID'].lower() + '-agent',
                                     environment=[f"MTC_AGENT_UUID={cfg['UUID'].upper()}-AGENT",
                                                  f"ADAPTER_UUID={cfg['UUID'].upper()}",
                                                  f"ADAPTER_IP={adapter_cfg['IP']}",
                                                  f"ADAPTER_PORT={adapter_cfg['PORT']}"],
                                     ports={'5000/tcp': agent_cfg['PORT']},
                                     command='mtcagent run agent.cfg',
                                     network=cfg['network'])

    _copy_files(agent, agent_cfg['DEVICES'])
    _insert_agent_to_db(db_engine, cfg['UUID'])
    return agent
