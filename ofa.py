import click
from sqlalchemy import create_engine

import config.config as config
import src.ofa as ofa


@click.group()
def main():
    """ Administrative tool for OpenFactory """
    pass


@click.group
def agent():
    """ Manage MTConnect agents """
    pass


@click.command()
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def create(yaml_config_file):
    """ Create an MTConnect agent based on a yaml configuration file """
    ofa.agent_create(yaml_config_file, db_engine)


@click.command()
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def run(yaml_config_file):
    """ Create and run an MTConnect agent based on a yaml configuration file """
    ofa.agent_run(yaml_config_file, db_engine)


@click.command()
@click.argument('agent_uuid',
                nargs=1)
def start(agent_uuid):
    """ Start an MTConnect agent with UUID AGENT_UUID """
    ofa.agent_start(agent_uuid, db_engine)


@click.command()
@click.argument('agent_uuid',
                nargs=1)
def stop(agent_uuid):
    """ Stop an MTConnect agent with UUID AGENT_UUID """
    ofa.agent_stop(agent_uuid, db_engine)


@click.command()
@click.argument('agent_uuid',
                nargs=1)
def rm(agent_uuid):
    """ Remove an MTConnect agent with UUID AGENT_UUID """
    ofa.agent_rm(agent_uuid, db_engine)


@click.command()
def ls():
    """ List MTConnect agents """
    ofa.agent_ls(db_engine)


@click.command()
@click.argument('agent_uuid',
                nargs=1)
def attach(agent_uuid):
    """ Attach an MTConnect agent """
    ofa.agent_attach(agent_uuid, db_engine)


@click.command()
@click.argument('agent_uuid',
                nargs=1)
def detach(agent_uuid):
    """ Detach an MTConnect agent """
    ofa.agent_detach(agent_uuid, db_engine)


@click.group
def device():
    """ Manage MTConnect devices """
    pass


@click.command(name='down')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def device_down(yaml_config_file):
    """ Stop and remove devices """
    ofa.device.down(yaml_config_file, db_engine)


@click.command(name='up')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def device_up(yaml_config_file):
    """ Create and start devices """
    ofa.device.up(yaml_config_file, db_engine)


main.add_command(agent)
agent.add_command(create)
agent.add_command(run)
agent.add_command(start)
agent.add_command(stop)
agent.add_command(rm)
agent.add_command(ls)
agent.add_command(attach)
agent.add_command(detach)

main.add_command(device)
device.add_command(device_down)
device.add_command(device_up)


if __name__ == '__main__':
    db_engine = create_engine(config.SQL_ALCHEMY_CONN)
    main()
