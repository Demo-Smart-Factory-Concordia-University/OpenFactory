import click
from pathlib import Path
from openfactory.config import load_yaml


@click.command(name='config')
def config():
    """ List configurations of OpenFactory """
    config_file = Path.joinpath(Path(__file__).resolve().parent.parent, 'config', 'openfactory.yml')
    conf = load_yaml(config_file)
    for key in conf:
        print(f"{key} = {conf[key]}")
