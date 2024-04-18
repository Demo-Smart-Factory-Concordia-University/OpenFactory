import click
from sqlalchemy import select

from openfactory.ofa.db import db
from openfactory.exceptions import OFAException
from openfactory.models.infrastack import InfraStack
from openfactory.models.user_notifications import user_notify


@click.command(name='rm')
@click.argument('stack_name', nargs=1)
def click_rm(stack_name):
    """ Remove an infrastructure stack defined in OpenFactory """
    query = select(InfraStack).where(InfraStack.stack_name == stack_name)
    stack = db.session.execute(query).one_or_none()
    if stack is None:
        user_notify.fail(f"No OpenFactory stack {stack_name} in OpenFactory database")
        return
    stack[0].clear()
    try:
        db.session.delete(stack[0])
        db.session.commit()
    except OFAException as err:
        db.session.rollback()
        user_notify.fail(err)
