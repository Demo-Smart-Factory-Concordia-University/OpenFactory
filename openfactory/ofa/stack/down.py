from sqlalchemy import select
from openfactory.utils import load_yaml
from openfactory.models.nodes import Node
from openfactory.exceptions import OFAException


def down(db_session, stack_config_file, user_notification=print, user_notification_fail=print):
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

        try:
            db_session.delete(n)
            db_session.commit()
            user_notification(f"Removed node {node}")
        except OFAException as err:
            db_session.rollback()
            user_notification_fail(err)

    if stack['manager']:
        if len(db_session.query(Node).all()) == 1:
            query = select(Node).where(Node.node_name == 'manager')
            manager = db_session.execute(query).one()
            try:
                db_session.delete(manager[0])
                db_session.commit()
                user_notification("Removed manager node")
            except OFAException as err:
                db_session.rollback()
                user_notification_fail(err)
        else:
            user_notification("Manager node not removed as other nodes exist")
