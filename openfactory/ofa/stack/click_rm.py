import click
from sqlalchemy import select

import openfactory.ofa as ofa
from openfactory.models.infrastack import InfraStack
from openfactory.ofa.db import db


@click.command(name='rm')
@click.argument('stack_name', nargs=1)
def click_rm(stack_name):
    """ Remove an infrastructure stack defined in OpenFactory """
    query = select(InfraStack).where(InfraStack.stack_name == stack_name)
    stack = db.session.execute(query).one_or_none()
    if stack is None:
        print(f"No OpenFactory stack {stack_name} in OpenFactory database")
        return
    ofa.stack.rm(db.session, stack[0].id)
