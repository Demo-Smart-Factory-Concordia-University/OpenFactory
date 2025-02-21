import asyncio
import json
from confluent_kafka import Producer
from pyksql.ksql import KSQL
import openfactory.config as config
from openfactory.exceptions import OFAException


class Asset():
    """
    OpenFactory Asset
    """

    def __init__(self, asset_uuid):
        self.ksql = KSQL(config.KSQLDB)
        self.asset_uuid = asset_uuid
        query = f"SELECT TYPE FROM assets WHERE DEVICE_UUID = '{asset_uuid}';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        if df.empty:
            raise OFAException(f"Asset {asset_uuid} is not deployed in OpenFactory")
        self.type = df['TYPE'][0]

    def attributes(self):
        """ returns all attributes of the asset """
        query = f"SELECT ID FROM devices WHERE device_uuid='{self.asset_uuid}' AND TYPE != 'Method';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return df.ID.tolist()

    def samples(self):
        """ return samples of asset """
        query = f"SELECT ID, VALUE, TYPE FROM devices WHERE key LIKE '{self.asset_uuid}|%';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return {row.ID: row.VALUE for row in df[df["TYPE"] == "Samples"].itertuples()}

    def events(self):
        """ return events of asset """
        query = f"SELECT ID, VALUE, TYPE FROM devices WHERE key LIKE '{self.asset_uuid}|%';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return {row.ID: row.VALUE for row in df[df["TYPE"] == "Events"].itertuples()}

    def conditions(self):
        """ return conditions of asset """
        query = f"SELECT ID, VALUE, TYPE FROM devices WHERE key LIKE '{self.asset_uuid}|%';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return {row.ID: row.VALUE for row in df[df["TYPE"] == "Condition"].itertuples()}

    def methods(self):
        """ return methods of asset """
        query = f"SELECT ID, VALUE, TYPE FROM devices WHERE key LIKE '{self.asset_uuid}|%';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return {row.ID: row.VALUE for row in df[df["TYPE"] == "Method"].itertuples()}

    def method(self, method, args=""):
        """ request execution of an asset method """
        print(f'Requesting execution of method {method}({args})')
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
        query = f"SELECT VALUE, TYPE FROM devices WHERE key LIKE '{self.asset_uuid}|{attribute_id}';"
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
