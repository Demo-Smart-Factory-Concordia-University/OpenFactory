""" ofa configuration listing command. """

import click
from pathlib import Path
from openfactory import ROOT_DIR
from openfactory.config import load_yaml


@click.command(name='ls')
def ls() -> None:
    """ List configurations of OpenFactory. """
    config_file = Path(ROOT_DIR).joinpath('config', 'openfactory.yml')
    conf = load_yaml(config_file)
    for key in conf:
        print(f"{key} = {conf[key]}")
