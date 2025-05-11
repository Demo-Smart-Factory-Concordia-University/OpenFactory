""" OpenFactory Command Line Interface. """

import click
import openfactory.ofa as ofa


@click.group()
def cli():
    """ Administrative tool for OpenFactory. """
    pass


@cli.group()
def nodes():
    """ Manage OpenFactory infrastructure. """
    pass


@cli.group()
def agent():
    """ Manage MTConnect agents. """
    pass


@cli.group()
def config():
    """ Manage OpenFactory configuration. """
    pass


@cli.group()
def device():
    """ Manage MTConnect devices. """
    pass


@cli.group()
def apps():
    """ Manage OpenFactory applications. """
    pass


@cli.group()
def asset():
    """ Manage OpenFactory assets. """
    pass


# Register commands
config.add_command(ofa.config.ls)

nodes.add_command(ofa.nodes.click_up)
nodes.add_command(ofa.nodes.click_down)
nodes.add_command(ofa.nodes.click_ls)

agent.add_command(ofa.agent.ls)

device.add_command(ofa.device.click_up)
device.add_command(ofa.device.click_down)
device.add_command(ofa.device.click_connect_influxdb)

apps.add_command(ofa.app.click_up)
apps.add_command(ofa.app.click_down)

asset.add_command(ofa.asset.register)
asset.add_command(ofa.asset.deregister)
