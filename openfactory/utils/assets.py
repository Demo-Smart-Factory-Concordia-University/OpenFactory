""" Asset registration and deregistration in OpenFactory. """

from openfactory.assets.utils import AssetAttribute
from openfactory.assets.kafka import AssetProducer
from openfactory.kafka.ksql import KSQLDBClient
import openfactory.config as config


def register_asset(asset_uuid: str, asset_type: str,
                   ksqlClient: KSQLDBClient, bootstrap_servers: str = config.KAFKA_BROKER, docker_service=""):
    """
    Register an asset in OpenFactory.

    Args:
        asset_uuid (str): UUID of the asset.
        asset_type (str): Type of the asset.
        ksqlClient: (KSQLDBClient) KSQL client for executing queries.
        bootstrap_servers (str): Kafka bootstrap server address.
        docker_service (str): Docker service name associated with the asset.
    """
    producer = AssetProducer(asset_uuid, ksqlClient, bootstrap_servers)

    producer.send_asset_attribute(
        "AssetType",
        AssetAttribute(value=asset_type, type="OpenFactory", tag="AssetType")
    )

    producer.send_asset_attribute(
        "DockerService",
        AssetAttribute(value=docker_service, type="OpenFactory", tag="DockerService")
    )

    # Initialize references
    for ref_id in ["references_below", "references_above"]:
        producer.send_asset_attribute(
            ref_id,
            AssetAttribute(value="", type="OpenFactory", tag="AssetsReferences")
        )


def deregister_asset(asset_uuid: str,
                     ksqlClient: KSQLDBClient, bootstrap_servers: str = config.KAFKA_BROKER):
    """
    Deregister an asset from OpenFactory.

    Args:
        asset_uuid (str): UUID of the asset.
        ksqlClient: (KSQLDBClient) KSQL client for executing queries.
        bootstrap_servers (str): Kafka bootstrap server address.
    """
    producer = AssetProducer(asset_uuid, ksqlClient, bootstrap_servers)

    # UNAVAILABLE message
    producer.send_asset_attribute(
        "avail",
        AssetAttribute(value="UNAVAILABLE", type="Events", tag="Availability")
    )

    # Remove references
    for ref_id in ["references_below", "references_above"]:
        producer.send_asset_attribute(
            ref_id,
            AssetAttribute(value="", type="OpenFactory", tag="AssetsReferences")
        )

    # tombstone message for table ASSETS
    producer.produce(topic=ksqlClient.get_kafka_topic('assets_type'),
                     key=asset_uuid,
                     value=None)

    # tombstone message for table DOCKER_SERVICES
    producer.produce(topic=ksqlClient.get_kafka_topic('docker_services'),
                     key=asset_uuid,
                     value=None)
    producer.flush()
