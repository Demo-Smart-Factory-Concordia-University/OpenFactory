import asyncio
import json
import re
import threading
from confluent_kafka import Producer
from pyksql.ksql import KSQL
import openfactory.config as config
from openfactory.exceptions import OFAException
from openfactory.kafka import KafkaAssetConsumer


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
        self._events_consumer_thread = None
        self._events_consumer_instance = None

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
    def references_above(self):
        """ References to above OpenFactory assets """
        query = f"SELECT VALUE, TYPE FROM assets WHERE key='{self.asset_uuid}|references_above';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        if df.empty or df['VALUE'][0].strip() == "":
            return []
        return [Asset(asset_uuid=asset_uuid.strip()) for asset_uuid in df['VALUE'][0].split(",")]

    def set_references_above(self, asset_references):
        """ Set references to above assets """
        msg = {
            "ID": "references_above",
            "VALUE": asset_references,
            "TAG": "AssetsReferences",
            "TYPE": "OpenFactory"
        }
        prod = Producer({'bootstrap.servers': config.KAFKA_BROKER})
        prod.produce(topic=self.ksql.get_kafka_topic('ASSETS_STREAM'),
                     key=self.asset_uuid,
                     value=json.dumps(msg))
        prod.flush()

    @property
    def references_below(self):
        """ References to below OpenFactory assets """
        query = f"SELECT VALUE, TYPE FROM assets WHERE key='{self.asset_uuid}|references_below';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        if df.empty or df['VALUE'][0].strip() == "":
            return []
        return [Asset(asset_uuid=asset_uuid.strip()) for asset_uuid in df['VALUE'][0].split(",")]

    def set_references_below(self, asset_references):
        """ Set references to below assets """
        msg = {
            "ID": "references_below",
            "VALUE": asset_references,
            "TAG": "AssetsReferences",
            "TYPE": "OpenFactory"
        }
        prod = Producer({'bootstrap.servers': config.KAFKA_BROKER})
        prod.produce(topic=self.ksql.get_kafka_topic('ASSETS_STREAM'),
                     key=self.asset_uuid,
                     value=json.dumps(msg))
        prod.flush()

    def add_reference_above(self, above_asset_reference):
        """ Adds a above-reference to the asset """
        query = f"SELECT VALUE FROM assets WHERE key='{self.asset_uuid}|references_above';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        if df.empty or df['VALUE'][0].strip() == "":
            references = above_asset_reference
        else:
            references = above_asset_reference + ', ' + df['VALUE'][0]
        msg = {
            "ID": "references_above",
            "VALUE": references,
            "TAG": "AssetsReferences",
            "TYPE": "OpenFactory"
        }
        prod = Producer({'bootstrap.servers': config.KAFKA_BROKER})
        prod.produce(topic=self.ksql.get_kafka_topic('ASSETS_STREAM'),
                     key=self.asset_uuid,
                     value=json.dumps(msg))
        prod.flush()

    def add_reference_below(self, below_asset_reference):
        """ Adds a below-reference to the asset """
        query = f"SELECT VALUE FROM assets WHERE key='{self.asset_uuid}|references_below';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        if df.empty or df['VALUE'][0].strip() == "":
            references = below_asset_reference
        else:
            references = below_asset_reference + ', ' + df['VALUE'][0]
        msg = {
            "ID": "references_below",
            "VALUE": references,
            "TAG": "AssetsReferences",
            "TYPE": "OpenFactory"
        }
        prod = Producer({'bootstrap.servers': config.KAFKA_BROKER})
        prod.produce(topic=self.ksql.get_kafka_topic('ASSETS_STREAM'),
                     key=self.asset_uuid,
                     value=json.dumps(msg))
        prod.flush()

    def __consume_events(self, topic, bootstrap_servers, kakfa_group_id, on_event):
        """ Kafka consumer that runs in a separate thread and calls `on_event` """

        class EventsConsumer(KafkaAssetConsumer):

            def filter_messages(self, msg_value):
                """ Filters out Events """
                if msg_value['type'] == 'Events':
                    return msg_value
                else:
                    return None

        self._events_consumer_instance = EventsConsumer(
            consumer_group_id=kakfa_group_id,
            asset_uuid=self.asset_uuid,
            on_message=on_event,
            bootstrap_servers=bootstrap_servers)
        self._events_consumer_instance.consume()

    def subscribe_to_events(self, on_event, kakfa_group_id):
        """ Subscribots to events messages of the Asset """
        self._events_consumer_thread = threading.Thread(
            target=self.__consume_events,
            args=(self.ksql.get_kafka_topic('ASSETS_STREAM'), config.KAFKA_BROKER, kakfa_group_id, on_event),
            daemon=True
        )
        self._events_consumer_thread.start()
        return self._events_consumer_thread

    def stop_events_subscription(self):
        """ Stop the Kafka consumer gracefully """
        if self._events_consumer_instance:
            self._events_consumer_instance.stop()
        if self._events_consumer_thread:
            self._events_consumer_thread.join()


if __name__ == "__main__":

    # Example usage of Asset
    cnc = Asset('PROVER3018')

    # list samples
    print(cnc.samples())
    print(cnc.Zact)

    # subscribe to events
    def on_event(msg_key, msg_value):
        """ Callback to process received events """
        print(f"[{msg_key}] {msg_value}")

    cnc.subscribe_to_events(on_event, 'demo_group')

    # run a main loop while subscription remains
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping consumer thread...")
        cnc.stop_events_subscription()
        print("Consumer stopped.")
