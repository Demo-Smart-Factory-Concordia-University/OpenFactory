import click
from openfactory.models.user_notifications import user_notify
import openfactory.ofa as ofa
from openfactory.docker.docker_access_layer import dal
from openfactory.ofa.db import db
import openfactory.config as config


@click.group()
def cli():
    """ Administrative tool for OpenFactory """
    pass


@click.group
def nodes():
    """ Manage OpenFactory infrastructure """
    pass


@click.group
def agent():
    """ Manage MTConnect agents """
    pass


@click.group
def device():
    """ Manage MTConnect devices """
    pass


cli.add_command(nodes)
nodes.add_command(ofa.nodes.click_up)
nodes.add_command(ofa.nodes.click_down)
nodes.add_command(ofa.nodes.click_ls)

cli.add_command(agent)
agent.add_command(ofa.agent.ls)
agent.add_command(ofa.agent.click_create)
agent.add_command(ofa.agent.run)
agent.add_command(ofa.agent.click_start)
agent.add_command(ofa.agent.click_stop)
agent.add_command(ofa.agent.click_rm)
agent.add_command(ofa.agent.click_attach)
agent.add_command(ofa.agent.click_detach)

cli.add_command(device)
device.add_command(ofa.device.click_up)
device.add_command(ofa.device.click_down)
device.add_command(ofa.device.click_connect_influxdb)

# setup user notifications
user_notify.setup(success_msg=lambda msg: print(f"{config.OFA_SUCCSESS}{msg}{config.OFA_END}"),
                  fail_msg=lambda msg: print(f"{config.OFA_FAIL}{msg}{config.OFA_END}"),
                  info_msg=print)

# connect to Docker engine
dal.connect()

# connect to database
db.conn_uri = config.SQL_ALCHEMY_CONN
db.connect()

if __name__ == '__main__':
    cli()
