import json
from datetime import datetime, timezone
from pyksql.ksql import KSQL
from confluent_kafka import Producer
import openfactory.config as config


def register_asset(asset_uuid, asset_type, docker_service="", ksqldb_url=config.KSQLDB, bootstrap_servers=config.KAFKA_BROKER):
    """ Register an asset in OpenFactory """
    ksql = KSQL(ksqldb_url)
    prod = Producer({'bootstrap.servers': bootstrap_servers})

    # Asset Type
    msg1 = {
        "ID": "AssetType",
        "VALUE": asset_type,
        "TAG": "AssetType",
        "TYPE": "OpenFactory",
        "attributes": {
                "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                }
    }
    prod.produce(topic=ksql.get_kafka_topic('ASSETS_STREAM'),
                 key=asset_uuid,
                 value=json.dumps(msg1))

    # Docker service
    msg2 = {
        "ID": "DockerService",
        "VALUE": docker_service,
        "TAG": "DockerService",
        "TYPE": "OpenFactory",
        "attributes": {
                "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                }
    }
    prod.produce(topic=ksql.get_kafka_topic('ASSETS_STREAM'),
                 key=asset_uuid,
                 value=json.dumps(msg2))

    prod.flush()


def deregister_asset(asset_uuid, ksqldb_url=config.KSQLDB, bootstrap_servers=config.KAFKA_BROKER):
    """ Deregister an asset from OpenFactory """
    ksql = KSQL(ksqldb_url)
    prod = Producer({'bootstrap.servers': bootstrap_servers})

    # UNAVAILABLE message
    msg = {
        "ID": "avail",
        "VALUE": "UNAVAILABLE",
        "TAG": "Availability",
        "TYPE": "Events"
    }
    assets_stream_topic = ksql.get_kafka_topic('ASSETS_STREAM')
    prod.produce(topic=assets_stream_topic,
                 key=asset_uuid,
                 value=json.dumps(msg))

    # remove references
    msg = {
        "ID": "references_below",
        "VALUE": "",
        "TAG": "AssetsReferences",
        "TYPE": "OpenFactory"
    }
    prod.produce(topic=assets_stream_topic,
                 key=asset_uuid,
                 value=json.dumps(msg))
    msg["ID"] = "references_above"
    prod.produce(topic=assets_stream_topic,
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
