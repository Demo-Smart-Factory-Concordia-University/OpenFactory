from sqlalchemy import select
from openfactory.utils import load_yaml
from openfactory.models.nodes import Node
from openfactory.models.infrastack import InfraStack
from openfactory.exceptions import OFAConfigurationException


def create_infra_stack(db_session, stack_config_file):
    """ Creates an infrastructure stack """

    # Load yaml description file
    infra = load_yaml(stack_config_file)

    # Build InfraStack model
    if 'stack' in infra:
        query = select(InfraStack).where(InfraStack.stack_name == infra['stack'])
        stack = db_session.execute(query).one_or_none()
        if stack is None:
            stack = InfraStack(
                stack_name=infra['stack']
            )
            db_session.add_all([stack])
            db_session.commit()
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
        db_session.add_all([node])
        db_session.commit()

    # attach nodes to swarm cluster
    for node_name, host in infra['nodes'].items():
        query = select(Node).where(Node.node_name == node_name)
        if db_session.execute(query).one_or_none() is None:
            print("Attaching ", node_name)
            node = Node(
                node_name=node_name,
                node_ip=host,
                stack=stack
            )
            db_session.add_all([node])
            db_session.commit()
