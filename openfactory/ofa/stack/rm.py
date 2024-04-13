from sqlalchemy import select
from openfactory.models.infrastack import InfraStack
from openfactory.models.nodes import Node
from openfactory.exceptions import OFAException


def rm(db_session, stack_id, user_notification_success=print, user_notification_fail=print):
    """ Removes an infrastructure stack """
    query = select(InfraStack).where(InfraStack.id == stack_id)
    stack = db_session.execute(query).one()
    stack = stack[0]
    stack_name = stack.stack_name
    for node in stack.nodes:
        if node.node_name == 'manager':
            continue
        try:
            node_name = node.node_name
            db_session.delete(node)
            db_session.commit()
            user_notification_success(f"Removed node {node_name}")
        except OFAException as err:
            db_session.rollback()
            user_notification_fail(err)

    if len(stack.nodes) == 1:
        if stack.nodes[0].node_name == 'manager':
            if len(db_session.query(Node).all()) == 1:
                try:
                    db_session.delete(stack.nodes[0])
                    db_session.commit()
                    user_notification_success("Removed manager node")
                except OFAException as err:
                    db_session.rollback()
                    user_notification_fail(err)
            else:
                user_notification_fail("Manager node not removed as other nodes exist")

    if stack.nodes:
        user_notification_success(f'Cleared successfully stack {stack_name}')
    else:
        db_session.delete(stack)
        db_session.commit()
        user_notification_success(f'Removed successfully stack {stack_name}')
