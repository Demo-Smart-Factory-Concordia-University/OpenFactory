import click
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from openfactory.utils import load_yaml
from openfactory.models.nodes import Node
from openfactory.models.infrastack import InfraStack
from openfactory.exceptions import OFAConfigurationException
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

    # Build stack
    if 'stack' in infra:
        query = select(InfraStack).where(InfraStack.stack_name == infra['stack'])
        stack = session.execute(query).one_or_none()
        if stack is None:
            stack = InfraStack(
                stack_name=infra['stack']
            )
            session.add_all([stack])
            session.commit()
        else:
            stack = stack[0]
            if ('manager' in infra) and (stack.manager is not None):
                if stack.manager.node_ip != infra['manager']:
                    raise OFAConfigurationException('Manager in configuration file differs from existing stack manager')
    else:
        stack = None

    if stack.manager is None:
        print("Setting up manager and network")
        node = Node(
            node_name='manager',
            node_ip=infra['manager'],
            network=infra['network'],
            stack=stack
        )
        session.add_all([node])
        session.commit()

    # attach nodes to swarm cluster
    for node_name, host in infra['nodes'].items():
        query = select(Node).where(Node.node_name == node_name)
        if session.execute(query).one_or_none() is None:
            print("Attaching ", node_name)
            node = Node(
                node_name=node_name,
                node_ip=host,
                stack=stack
            )
            session.add_all([node])
            session.commit()

    session.close()
