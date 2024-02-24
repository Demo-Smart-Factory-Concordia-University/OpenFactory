import click
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from openfactory.utils import load_yaml
from openfactory.models.nodes import Node
import openfactory.config as config


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

    print("Setting up manager and network")
    node = Node(
        node_name='manager',
        node_ip=infra['manager'],
        network=infra['network']
    )
    session.add_all([node])
    session.commit()

    # attach nodes to swarm cluster
    for node, host in infra['nodes'].items():
        print("Attaching ", node)
        node = Node(
            node_name=node,
            node_ip=host
        )
        session.add_all([node])
        session.commit()

    session.close()
