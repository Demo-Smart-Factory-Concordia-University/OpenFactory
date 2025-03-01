import asyncio
import json
import re
from confluent_kafka import Producer
from pyksql.ksql import KSQL
import openfactory.config as config
from openfactory.exceptions import OFAException


class Asset():
    """
    OpenFactory Asset
    """

    def __init__(self, asset_uuid, ksqldb_url=config.KSQLDB):
        self.ksql = KSQL(ksqldb_url)
        self.asset_uuid = asset_uuid
        query = f"SELECT TYPE FROM assets_type WHERE ASSET_UUID='{asset_uuid}';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        if df.empty:
            raise OFAException(f"Asset {asset_uuid} is not deployed in OpenFactory")
        self.type = df['TYPE'][0]

    def attributes(self):
        """ returns all attributes of the asset """
        query = f"SELECT ID FROM assets WHERE asset_uuid='{self.asset_uuid}' AND TYPE != 'Method';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return df.ID.tolist()

    def samples(self):
        """ return samples of asset """
        query = f"SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='{self.asset_uuid}' AND TYPE='Samples';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return {row.ID: row.VALUE for row in df.itertuples()}

    def events(self):
        """ return events of asset """
        query = f"SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='{self.asset_uuid}' AND TYPE='Events';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return {row.ID: row.VALUE for row in df.itertuples()}

    def conditions(self):
        """ return conditions of asset """
        query = f"SELECT ID, VALUE, TAG, TYPE FROM assets WHERE ASSET_UUID='{self.asset_uuid}' AND TYPE='Condition';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return [{
            "ID": row.ID,
            "VALUE": row.VALUE,
            "TAG": re.sub(r'\{.*?\}', '', row.TAG).strip()}
            for row in df.itertuples()]

    def methods(self):
        """ return methods of asset """
        query = f"SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='{self.asset_uuid}' AND TYPE='Method';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return {row.ID: row.VALUE for row in df.itertuples()}

    def method(self, method, args=""):
        """ request execution of an asset method """
        msg = {
            "CMD": method,
            "ARGS": args
        }
        prod = Producer({'bootstrap.servers': config.KAFKA_BROKER})
        prod.produce(topic=self.ksql.get_kafka_topic('CMDS_STREAM'),
                     key=self.asset_uuid,
                     value=json.dumps(msg))
        prod.flush()

    def __getattr__(self, attribute_id):
        """ Allow accessing samples, events, conditions and methods as attributes """
        query = f"SELECT VALUE, TYPE FROM assets WHERE key='{self.asset_uuid}|{attribute_id}';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        if df.empty:
            raise AttributeError(f"Asset {self.asset_uuid} has no attribute '{attribute_id}'")

        if df['TYPE'][0] == 'Samples':
            return float(df['VALUE'][0])

        if df['TYPE'][0] == 'Method':
            def method_caller(*args, **kwargs):
                args_str = " ".join(map(str, args))
                return self.method(attribute_id, args_str)
            return method_caller

        return df['VALUE'][0]

    @property
    def references(self):
        """ References to other OpenFactory assets """
        query = f"SELECT VALUE, TYPE FROM assets WHERE key='{self.asset_uuid}|references';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        if df.empty:
            return []
        return [Asset(asset_uuid=asset_uuid.strip()) for asset_uuid in df['VALUE'][0].split(",")]

    def set_references(self, asset_references):
        """ Set references to other assets """
        msg = {
            "ID": "references",
            "VALUE": asset_references,
            "TAG": "AssetsReferences",
            "TYPE": "OpenFactory"
        }
        prod = Producer({'bootstrap.servers': config.KAFKA_BROKER})
        prod.produce(topic=self.ksql.get_kafka_topic('ASSETS_STREAM'),
                     key=self.asset_uuid,
                     value=json.dumps(msg))
        prod.flush()
