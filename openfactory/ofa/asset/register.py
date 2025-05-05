""" ofa asset register command. """

import click
from openfactory.utils import register_asset
from openfactory.ofa.ksqldb import ksql


@click.command(name='register')
@click.argument('asset_uuid')
@click.argument('asset_type')
@click.option("--docker-service", "-d", default="", help="Docker service name (optional)")
def register(asset_uuid: str, asset_type: str, docker_service: str) -> None:
    """
    Register an OpenFactory asset.

    Args:
        asset_uuid (str): The UUID of the asset to register.
        asset_type (str): The type of the asset to register.
        docker_service (str): The Docker service name (optional).
    """
    print(f"Registering {asset_uuid}")
    register_asset(asset_uuid=asset_uuid,
                   asset_type=asset_type,
                   ksqlClient=ksql.client,
                   docker_service=docker_service)
