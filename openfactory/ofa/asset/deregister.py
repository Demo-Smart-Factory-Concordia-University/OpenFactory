""" ofa asset deregister command. """

import click
from openfactory.utils import deregister_asset
from openfactory.ofa.ksqldb import ksql


@click.command(name='deregister')
@click.argument('asset_uuid')
def deregister(asset_uuid: str) -> None:
    """
    Deregister an OpenFactory asset.

    Args:
        asset_uuid (str): The UUID of the asset to deregister.
    """
    print(f"Dergestering {asset_uuid}")
    deregister_asset(asset_uuid=asset_uuid, ksqlClient=ksql.client)
