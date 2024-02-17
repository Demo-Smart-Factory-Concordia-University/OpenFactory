import docker
from sqlalchemy import select
from sqlalchemy.orm import Session
from openfactory.utils import load_yaml
from openfactory.models.nodes import Node
import config.config as config


def down(yaml_config_file, db_engine):
    """ Tear down OpenFactory infrastructure """

    session = Session(db_engine)

    # Load yaml description file
    infra = load_yaml(yaml_config_file)

    for node, host in infra['nodes'].items():
        print("Detaching", node)
        rem_client = docker.DockerClient(base_url="ssh://" + config.OPENFACTORY_USER + "@" + host)
        rem_client.swarm.leave()
        rem_client.close()
        query = select(Node).where(Node.node_name == node)
        for n in session.scalars(query):
            session.delete(n)

    print("Shutting down manager")
    client = docker.DockerClient(base_url="ssh://" + config.OPENFACTORY_USER + "@" + infra['manager'])
    client.swarm.leave(force=True)
    query = select(Node).where(Node.node_name == 'manager')
    for node in session.scalars(query):
        session.delete(node)

    session.commit()
    client.close()
