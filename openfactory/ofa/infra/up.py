import click
import docker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from openfactory.utils import load_yaml
from openfactory.models.nodes import Node
import config.config as config


@click.command(name='up')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def up(yaml_config_file):
    """ Setup OpenFactory infrastructure """

    db_engine = create_engine(config.SQL_ALCHEMY_CONN)
    session = Session(db_engine)

    # Load yaml description file
    infra = load_yaml(yaml_config_file)

    print("Setting up manager")
    client = docker.DockerClient(base_url="ssh://" + config.OPENFACTORY_USER + "@" + infra['manager'])
    client.swarm.init(advertise_addr=infra['manager'])
    token = client.swarm.attrs['JoinTokens']['Worker']
    node = Node(
        node_name='manager',
        node_ip=infra['manager']
    )
    session.add_all([node])

    # create overlay network
    print("Create network")
    client.networks.create(infra['network'],
                           driver='overlay',
                           attachable=True)

    # attach nodes to swarm cluster
    for node, host in infra['nodes'].items():
        print("Attaching ", node)
        rem_client = docker.DockerClient(base_url="ssh://" + config.OPENFACTORY_USER + "@" + host)
        rem_client.swarm.join([infra['manager']], join_token=token)
        rem_client.close()
        node = Node(
            node_name=node,
            node_ip=host
        )
        session.add_all([node])

    session.commit()
    client.close()
