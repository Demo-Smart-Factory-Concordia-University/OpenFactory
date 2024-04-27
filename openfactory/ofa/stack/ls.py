import click
from sqlalchemy import select

from openfactory.models.infrastack import InfraStack
from openfactory.ofa.db import db


@click.command(name='ls')
@click.option('-v', '--verbose', 'verbose',
              flag_value='verbose', default=False,
              help='Increase verbosity')
def click_ls(verbose):
    """ List infrastructure stacks defined in OpenFactory """
    stacks = select(InfraStack)
    for stack in db.session.scalars(stacks):
        print(f'{stack.stack_name}:')
        for node in stack.nodes:
            print(f'  {node.node_name:15} {node.cpus:3} cpus    {node.status}')
            if verbose:
                for cont in node.containers:
                    print(f'    • {cont.name:20} {cont.cpus:3} cpus   {cont.status}')
