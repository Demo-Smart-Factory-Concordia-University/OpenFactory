import click
from sqlalchemy import select

import openfactory.ofa as ofa
from openfactory.models.infrastack import InfraStack
from openfactory.ofa.db import db
from .rm import rm


@click.command(name='rm')
@click.argument('stack_name', nargs=1)
def click_rm(stack_name):
    """ Remove an infrastructure stack defined in OpenFactory """
    query = select(InfraStack).where(InfraStack.stack_name == stack_name)
    stack = db.session.execute(query).one_or_none()
    if stack is None:
        ofa.fail_msg(f"No OpenFactory stack {stack_name} in OpenFactory database")
        return
    rm(db.session, stack[0].id,
       user_notification_success=ofa.success_msg,
       user_notification_fail=ofa.fail_msg)
