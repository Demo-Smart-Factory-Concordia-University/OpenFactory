from sqlalchemy import select
from openfactory.utils import load_yaml
from openfactory.models.user_notifications import user_notify
from openfactory.models.nodes import Node
from openfactory.models.infrastack import InfraStack
from openfactory.exceptions import OFAException


def remove_infrastack(db_session, stack_config_file):
    """
    Tear down an infrastructure stack based on a config file
    """
    # Load yaml description file
    stack = load_yaml(stack_config_file)

    for node, host in stack['nodes'].items():
        query = select(Node).where(Node.node_name == node)
        n = db_session.execute(query).one_or_none()
        if n:
            try:
                db_session.delete(n[0])
                db_session.commit()
            except OFAException as err:
                db_session.rollback()
                user_notify.info(err)

    if 'manager' in stack:
        query = select(Node).where(Node.node_name == 'manager')
        manager = db_session.execute(query).one_or_none()
        if manager:
            try:
                db_session.delete(manager[0])
                db_session.commit()
            except OFAException as err:
                db_session.rollback()
                user_notify.info(err)

    # remove stack
    if 'stack' in stack:
        query = select(InfraStack).where(InfraStack.stack_name == stack['stack'])
        infra_stack = db_session.execute(query).one_or_none()
        if infra_stack:
            try:
                db_session.delete(infra_stack[0])
                db_session.commit()
                user_notify.success(f"Removed successfully stack '{stack['stack']}'")
            except OFAException as err:
                db_session.rollback()
                user_notify.fail(err)
