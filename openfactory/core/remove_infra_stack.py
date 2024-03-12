from openfactory.models.infrastack import InfraStack


def remove_infra_stack(db_session, stack_id, user_notification_success=print, user_notification_fail=print):
    """ Removes an infrastructure stack """
    query = db_session.query(InfraStack).where(InfraStack.id == stack_id)
    stack = db_session.execute(query).one()
    stack = stack[0]
    stack_name = stack.stack_name
    for node in stack.nodes:
        if node.containers or node.compose_projects:
            user_notification_fail(f"Cannot remove node {node.node_name} as containers/Docker compose projects are running on it")
        else:
            node_name = node.node_name
            db_session.delete(node)
            db_session.commit()
            user_notification_success(f"Removed node {node_name}")
            print(f"Removed node {node_name}")
    if stack.nodes:
        user_notification_success(f'Cleared successfully stack {stack_name}')
    else:
        db_session.delete(stack)
        user_notification_success(f'Removed successfully stack {stack_name}')
        print(f'Removed successfully stack {stack_name}')
