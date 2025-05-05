""" ofa agent ls command. """

import click
from openfactory import OpenFactory
from openfactory.ofa.ksqldb import ksql


@click.command(name='ls')
def ls() -> None:
    """ List MTConnect agents defined in OpenFactory. """
    ofa = OpenFactory(ksqlClient=ksql.client)
    print('UUID                      AVAILABILITY              PORT')
    for agent in ofa.agents():
        print(f'{agent.asset_uuid:25} {agent.agent_avail.value:25} {agent.agent_port.value}')
