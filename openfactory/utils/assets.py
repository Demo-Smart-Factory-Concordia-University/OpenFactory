import json
from pyksql.ksql import KSQL
from confluent_kafka import Producer
import openfactory.config as config


def register_asset(asset_uuid, asset_type):
    """ Register an asset in OpenFactory """
    msg = {
        "ID": "AssetType",
        "VALUE": asset_type,
        "TAG": "AssetType",
        "TYPE": "OpenFactory"
    }
    ksql = KSQL(config.KSQLDB)
    prod = Producer({'bootstrap.servers': config.KAFKA_BROKER})
    prod.produce(topic=ksql.get_kafka_topic('DEVICES_STREAM'),
                 key=asset_uuid,
                 value=json.dumps(msg))
    prod.flush()
