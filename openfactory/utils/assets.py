from openfactory.assets import AssetProducer, AssetAttribute
import openfactory.config as config


def register_asset(asset_uuid, asset_type, ksqlClient, bootstrap_servers=config.KAFKA_BROKER, docker_service=""):
    """ Register an asset in OpenFactory """

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


def deregister_asset(asset_uuid, ksqlClient, bootstrap_servers=config.KAFKA_BROKER):
    """ Deregister an asset from OpenFactory """
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
