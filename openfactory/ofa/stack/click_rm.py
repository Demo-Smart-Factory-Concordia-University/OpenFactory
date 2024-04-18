import click
from sqlalchemy import select

from openfactory.models.infrastack import InfraStack
from openfactory.ofa.db import db
from openfactory.models.user_notifications import user_notify
from .rm import rm


@click.command(name='rm')
@click.argument('stack_name', nargs=1)
def click_rm(stack_name):
    """ Remove an infrastructure stack defined in OpenFactory """
    query = select(InfraStack).where(InfraStack.stack_name == stack_name)
    stack = db.session.execute(query).one_or_none()
    if stack is None:
        user_notify.fail(f"No OpenFactory stack {stack_name} in OpenFactory database")
        return
    rm(db.session, stack[0].id,
       user_notification_success=user_notify.success,
       user_notification_fail=user_notify.fail)
