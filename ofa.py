import click
from openfactory.models.user_notifications import user_notify
import openfactory.ofa as ofa
from openfactory.ofa.db import db
import openfactory.config as config


@click.group()
def cli():
    """ Administrative tool for OpenFactory """
    pass


@click.group
def stack():
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


cli.add_command(stack)
stack.add_command(ofa.stack.click_up)
stack.add_command(ofa.stack.click_down)
stack.add_command(ofa.stack.click_ls)
stack.add_command(ofa.stack.click_rm)

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

# setup user notifications
user_notify.setup(success_msg=lambda msg: print(f"{config.OFA_SUCCSESS}{msg}{config.OFA_END}"),
                  fail_msg=lambda msg: print(f"{config.OFA_FAIL}{msg}{config.OFA_END}"),
                  info_msg=print)


# connect to database
db.conn_uri = config.SQL_ALCHEMY_CONN
db.connect()

if __name__ == '__main__':
    cli()
