import click
from sqlalchemy import create_engine

import config.config as config
import src.ofa as ofa


@click.group()
def main():
    """ Administrative tool for OpenFactory """
    pass


@click.group
def infra():
    """ Manage OpenFactory infrastructure """
    pass


@click.command(name='up')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def infra_up(yaml_config_file):
    """ Setup OpenFactory infrastructure """
    ofa.infra.up(yaml_config_file)


@click.command(name='down')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def infra_down(yaml_config_file):
    """ Tear down OpenFactory infrastructure """
    ofa.infra.down(yaml_config_file)


@click.group
def agent():
    """ Manage MTConnect agents """
    pass


@click.command(name='create')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def agent_create(yaml_config_file):
    """ Create an MTConnect agent based on a yaml configuration file """
    ofa.agent.create(yaml_config_file, db_engine)


@click.command(name='run')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def agent_run(yaml_config_file):
    """ Create and run an MTConnect agent based on a yaml configuration file """
    ofa.agent.run(yaml_config_file, db_engine)


@click.command(name='start')
@click.argument('agent_uuid',
                nargs=1)
def agent_start(agent_uuid):
    """ Start an MTConnect agent with UUID AGENT_UUID """
    ofa.agent.start(agent_uuid, db_engine)


@click.command(name='stop')
@click.argument('agent_uuid',
                nargs=1)
def agent_stop(agent_uuid):
    """ Stop an MTConnect agent with UUID AGENT_UUID """
    ofa.agent.stop(agent_uuid, db_engine)


@click.command(name='rm')
@click.argument('agent_uuid',
                nargs=1)
def agent_rm(agent_uuid):
    """ Remove an MTConnect agent with UUID AGENT_UUID """
    ofa.agent.rm(agent_uuid, db_engine)


@click.command(name='ls')
def agent_ls():
    """ List MTConnect agents """
    ofa.agent.ls(db_engine)


@click.command(name='attach')
@click.argument('agent_uuid',
                nargs=1)
def agent_attach(agent_uuid):
    """ Attach an MTConnect agent """
    ofa.agent.attach(agent_uuid, db_engine)


@click.command(name='detach')
@click.argument('agent_uuid',
                nargs=1)
def agent_detach(agent_uuid):
    """ Detach an MTConnect agent """
    ofa.agent.detach(agent_uuid, db_engine)


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


main.add_command(infra)
infra.add_command(infra_up)
infra.add_command(infra_down)

main.add_command(agent)
agent.add_command(agent_create)
agent.add_command(agent_run)
agent.add_command(agent_start)
agent.add_command(agent_stop)
agent.add_command(agent_rm)
agent.add_command(agent_ls)
agent.add_command(agent_attach)
agent.add_command(agent_detach)

main.add_command(device)
device.add_command(device_down)
device.add_command(device_up)


if __name__ == '__main__':
    db_engine = create_engine(config.SQL_ALCHEMY_CONN)
    main()
