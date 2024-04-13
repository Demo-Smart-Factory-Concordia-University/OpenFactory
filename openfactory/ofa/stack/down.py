from sqlalchemy import select
from openfactory.utils import load_yaml
from openfactory.models.nodes import Node


def down(db_session, stack_config_file, user_notification=print):
    """
    Tear down an infrastructure stack
    """
    # Load yaml description file
    stack = load_yaml(stack_config_file)

    for node, host in stack['nodes'].items():
        query = select(Node).where(Node.node_name == node)
        n = db_session.execute(query).one_or_none()
        if n:
            n = n[0]
        else:
            continue

        if n.containers or n.compose_projects:
            user_notification(f"Cannot remove node {n.node_name} as containers/Docker compose projects are running on it")
            continue

        db_session.delete(n)
        db_session.commit()
        user_notification(f"Removed node {node}")

    if stack['manager']:
        if len(db_session.query(Node).all()) == 1:
            query = select(Node).where(Node.node_name == 'manager')
            manager = db_session.execute(query).one()
            if manager[0].containers or manager[0].compose_projects:
                user_notification("Cannot remove manager node as containers/Docker compose projects are running on it")
                return
            db_session.delete(manager[0])
            db_session.commit()
            user_notification("Removed manager node")
        else:
            user_notification("Manager node not removed as other nodes exist")
