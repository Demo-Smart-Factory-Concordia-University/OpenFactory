import json
from pyksql.ksql import KSQL
from confluent_kafka import Producer
import openfactory.config as config


def register_asset(asset_uuid, asset_type, docker_service=""):
    """ Register an asset in OpenFactory """
    ksql = KSQL(config.KSQLDB)
    prod = Producer({'bootstrap.servers': config.KAFKA_BROKER})

    # Asset Type
    msg1 = {
        "ID": "AssetType",
        "VALUE": asset_type,
        "TAG": "AssetType",
        "TYPE": "OpenFactory"
    }
    prod.produce(topic=ksql.get_kafka_topic('ASSETS_STREAM'),
                 key=asset_uuid,
                 value=json.dumps(msg1))

    # Docker service
    msg2 = {
        "ID": "DockerService",
        "VALUE": docker_service,
        "TAG": "DockerService",
        "TYPE": "OpenFactory"
    }
    prod.produce(topic=ksql.get_kafka_topic('ASSETS_STREAM'),
                 key=asset_uuid,
                 value=json.dumps(msg2))

    prod.flush()


def deregister_asset(asset_uuid):
    """ Deregister an asset from OpenFactory """
    ksql = KSQL(config.KSQLDB)
    prod = Producer({'bootstrap.servers': config.KAFKA_BROKER})

    # UNAVAILABLE message
    msg = {
        "ID": "avail",
        "VALUE": "UNAVAILABLE",
        "TAG": "Availability",
        "TYPE": "Events"
    }
    prod.produce(topic=ksql.get_kafka_topic('ASSETS_STREAM'),
                 key=asset_uuid,
                 value=json.dumps(msg))

    # tombstone message for table ASSETS
    prod.produce(topic=ksql.get_kafka_topic('assets_type'),
                 key=asset_uuid,
                 value=None)

    # tombstone message for table DOCKER_SERVICES
    prod.produce(topic=ksql.get_kafka_topic('docker_services'),
                 key=asset_uuid,
                 value=None)
    prod.flush()
