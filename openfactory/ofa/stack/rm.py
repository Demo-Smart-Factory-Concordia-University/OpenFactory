from openfactory.models.infrastack import InfraStack
from openfactory.models.nodes import Node


def rm(db_session, stack_id, user_notification_success=print, user_notification_fail=print):
    """ Removes an infrastructure stack """
    query = db_session.query(InfraStack).where(InfraStack.id == stack_id)
    stack = db_session.execute(query).one()
    stack = stack[0]
    stack_name = stack.stack_name
    for node in stack.nodes:
        if node.node_name == 'manager':
            continue
        if node.containers or node.compose_projects:
            user_notification_fail(f"Cannot remove node {node.node_name} as containers/Docker compose projects are running on it")
        else:
            node_name = node.node_name
            db_session.delete(node)
            db_session.commit()
            user_notification_success(f"Removed node {node_name}")

    if len(stack.nodes) == 1:
        if stack.nodes[0].node_name == 'manager':
            if len(db_session.query(Node).all()) == 1:
                db_session.delete(stack.nodes[0])
                db_session.commit()
                user_notification_success("Removed manager node")
            else:
                user_notification_fail("Manager node not removed as other nodes exist")

    if stack.nodes:
        user_notification_success(f'Cleared successfully stack {stack_name}')
    else:
        db_session.delete(stack)
        db_session.commit()
        user_notification_success(f'Removed successfully stack {stack_name}')
