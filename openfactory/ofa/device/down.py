import click
import yaml
import openfactory.ofa as ofa


@click.command(name='down')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def down(yaml_config_file):
    """ Stop and remove devices """

    # Load yaml description file
    with open(yaml_config_file, 'r') as stream:
        cfg = yaml.safe_load(stream)

    for dev in cfg['devices']:
        device = cfg['devices'][dev]
        agent_uuid = device['UUID'].upper() + "-AGENT"
        ofa.agent.stop(agent_uuid)
        ofa.agent.detach(agent_uuid)
        ofa.agent.rm(agent_uuid)
