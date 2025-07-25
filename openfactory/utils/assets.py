""" Asset registration and deregistration in OpenFactory. """

import json
from typing import Dict
from datetime import datetime, timezone
from openfactory.assets.utils import AssetAttribute
from openfactory.kafka import AssetProducer
from openfactory.kafka.ksql import KSQLDBClient
import openfactory.config as config


def now_iso_to_epoch_millis() -> int:
    """
    Get the current UTC time as epoch milliseconds, suitable for Kafka TIMESTAMP fields.

    Returns:
        int: The current time in milliseconds since the Unix epoch.
    """
    now = datetime.now(timezone.utc)
    return int(now.timestamp() * 1000)


def register_asset(asset_uuid: str, uns: Dict, asset_type: str,
                   ksqlClient: KSQLDBClient, bootstrap_servers: str = config.KAFKA_BROKER, docker_service=""):
    """
    Register an asset in OpenFactory.

    Args:
        asset_uuid (str): UUID of the asset.
        uns (dict): UNS data with 'levels' (a dict of hierarchy levels) and 'uns_id' (UNS id as a string).
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

    if uns:
        # Set UNS levels
        for level_name, level_value in uns['levels'].items():
            producer.send_asset_attribute(
                level_name,
                AssetAttribute(value=level_value, type="OpenFactory", tag="UNSLevel")
            )
        # Set UNS map
        producer.produce(
            topic=ksqlClient.get_kafka_topic('asset_to_uns_map_raw'),
            key=asset_uuid.encode('utf-8'),
            value=json.dumps({
                'ASSET_UUID': asset_uuid,
                'UNS_ID': uns['uns_id'],
                'UNS_LEVELS': uns['levels'],
                'UPDATED_AT': now_iso_to_epoch_millis()
            })
        )
        producer.flush()


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

    # remove references
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

    # remove UNS map
    producer.produce(
        topic=ksqlClient.get_kafka_topic('asset_to_uns_map_raw'),
        key=asset_uuid,
        value=json.dumps({
            'asset_uuid': asset_uuid,
            'uns_id': None,
            'uns_levels': None,
            'updated_at': now_iso_to_epoch_millis()
        })
    )
    producer.flush()
