from sqlalchemy import select
from openfactory.utils import load_yaml
from openfactory.models.nodes import Node
from openfactory.models.infrastack import InfraStack
from openfactory.exceptions import OFAException


def down(db_session, stack_config_file, user_notification_success=print, user_notification_fail=print):
    """
    Tear down an infrastructure stack based on config file
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
        except OFAException as err:
            db_session.rollback()
            user_notification_fail(err)

    if 'manager' in stack:
        if len(db_session.query(Node).all()) == 1:
            query = select(Node).where(Node.node_name == 'manager')
            manager = db_session.execute(query).one()
            try:
                db_session.delete(manager[0])
                db_session.commit()
            except OFAException as err:
                db_session.rollback()
                user_notification_fail(err)
        else:
            user_notification_fail("Manager node not removed as other nodes exist")

    # remove stack if stack empty
    if 'stack' in stack:
        query = select(InfraStack).where(InfraStack.stack_name == stack['stack'])
        infra_stack = db_session.execute(query).one_or_none()
        if infra_stack:
            try:
                db_session.delete(infra_stack[0])
                db_session.commit()
                user_notification_success(f"Removed successfully stack '{stack['stack']}'")
            except OFAException as err:
                db_session.rollback()
                user_notification_fail(err)
