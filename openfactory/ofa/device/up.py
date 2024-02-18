import click
import openfactory.ofa as ofa


@click.command(name='up')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def up(yaml_config_file):
    """ Create and start devices """
    ofa.agent.create(yaml_config_file, run=True, attach=True)
