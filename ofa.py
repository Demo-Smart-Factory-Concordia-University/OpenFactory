import click
import openfactory.ofa as ofa


@click.group()
def cli():
    """ Administrative tool for OpenFactory """
    pass


@click.group
def infra():
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


cli.add_command(infra)
infra.add_command(ofa.infra.up)
infra.add_command(ofa.infra.down)

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
device.add_command(ofa.device.up)
device.add_command(ofa.device.down)


if __name__ == '__main__':
    cli()
