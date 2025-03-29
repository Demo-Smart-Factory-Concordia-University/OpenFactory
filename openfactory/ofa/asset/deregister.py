import click
from openfactory.utils import deregister_asset


@click.command(name='deregister')
@click.argument('asset_uuid')
def deregister(asset_uuid):
    """ Deregister an OpenFactory asset """
    print(f"Dergestering {asset_uuid}")
    deregister_asset(asset_uuid=asset_uuid)
