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
    prod.produce(topic=ksql.get_kafka_topic('DEVICES_STREAM'),
                 key=asset_uuid,
                 value=json.dumps(msg1))

    # Docker service
    msg2 = {
        "ID": "DockerService",
        "VALUE": docker_service,
        "TAG": "DockerService",
        "TYPE": "OpenFactory"
    }
    prod.produce(topic=ksql.get_kafka_topic('DEVICES_STREAM'),
                 key=asset_uuid,
                 value=json.dumps(msg2))

    prod.flush()


def deregister_asset(asset_uuid):
    """ Deregister an asset from OpenFactory """
    ksql = KSQL(config.KSQLDB)

    # tombstone message for table ASSETS
    prod = Producer({'bootstrap.servers': config.KAFKA_BROKER})
    prod.produce(topic=ksql.get_kafka_topic('assets'),
                 key=asset_uuid,
                 value=None)
    prod.flush()

    # tombstone message for table DOCKER_SERVICES
    prod = Producer({'bootstrap.servers': config.KAFKA_BROKER})
    prod.produce(topic=ksql.get_kafka_topic('docker_services'),
                 key=asset_uuid,
                 value=None)
    prod.flush()
