import asyncio
import json
import re
import threading
import uuid
from confluent_kafka import Producer, KafkaError
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pyksql.ksql import KSQL
from typing import Union
import openfactory.config as config
from openfactory.kafka import KafkaAssetConsumer, CaseInsensitiveDict


def current_timestamp():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


@dataclass
class AssetAttribute:
    value: Union[str, int]
    type: str
    tag: str
    timestamp: str = field(default_factory=current_timestamp)


class AssetProducer(Producer):
    """
    Kafka producer for an OpenFactory asset
    """
    def __init__(self, asset_uuid, ksqldb_url=config.KSQLDB, bootstrap_servers=config.KAFKA_BROKER):
        super().__init__({'bootstrap.servers': bootstrap_servers})
        self.ksql = KSQL(ksqldb_url)
        self.topic = self.ksql.get_kafka_topic('ASSETS_STREAM')
        self.asset_uuid = asset_uuid

    def send_asset_attribute(self, assetID, assetAttribute):
        """ Send Kafka messgage for an Asset attribute """
        msg = {
            "ID": assetID,
            "VALUE": assetAttribute.value,
            "TAG": assetAttribute.tag,
            "TYPE": assetAttribute.type,
            "attributes": {
                "timestamp": assetAttribute.timestamp
                }
        }
        self.produce(topic=self.topic,
                     key=self.asset_uuid,
                     value=json.dumps(msg))
        self.flush()


class Asset():
    """
    OpenFactory Asset
    """
    def __init__(self, asset_uuid, ksqldb_url=config.KSQLDB, bootstrap_servers=config.KAFKA_BROKER):
        super().__setattr__('asset_uuid', asset_uuid)
        super().__setattr__('ksqldb_url', ksqldb_url)
        super().__setattr__('ksql', KSQL(ksqldb_url))
        super().__setattr__('bootstrap_servers', bootstrap_servers)
        super().__setattr__('producer', AssetProducer(asset_uuid, bootstrap_servers=bootstrap_servers, ksqldb_url=ksqldb_url))

    @property
    def type(self):
        query = f"SELECT TYPE FROM assets_type WHERE ASSET_UUID='{self.asset_uuid}';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        if df.empty:
            return 'UNAVAILABLE'
        return df['TYPE'][0]

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
        prod = Producer({'bootstrap.servers': self.bootstrap_servers})
        prod.produce(topic=self.ksql.get_kafka_topic('CMDS_STREAM'),
                     key=self.asset_uuid,
                     value=json.dumps(msg))
        prod.flush()

    def __getattr__(self, attribute_id):
        """ Allow accessing samples, events, conditions and methods as attributes """
        query = f"SELECT VALUE, TYPE, TAG, TIMESTAMP FROM assets WHERE key='{self.asset_uuid}|{attribute_id}';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))

        if df.empty:
            return AssetAttribute(value='UNAVAILABLE',
                                  type='UNAVAILABLE',
                                  tag='UNAVAILABLE',
                                  timestamp='UNAVAILABLE')

        if df['TYPE'][0] == 'Method':
            def method_caller(*args, **kwargs):
                args_str = " ".join(map(str, args))
                return self.method(attribute_id, args_str)
            return method_caller

        ret = AssetAttribute(
            value=float(df['VALUE'][0]) if df['TYPE'][0] == 'Samples' and df['VALUE'][0] != 'UNAVAILABLE' else df['VALUE'][0],
            type=df['TYPE'][0],
            tag=df['TAG'][0],
            timestamp=df['TIMESTAMP'][0]
        )

        return ret

    def __setattr__(self, name, value):
        """ Set Asset attributes """

        # if not an Asset attributes, handle it as a class attribute
        if name not in self.attributes():
            super().__setattr__(name, value)
            return

        # send kafka message
        attr = self.__getattr__(name)
        self.producer.send_asset_attribute(name,
                                           AssetAttribute(
                                               value=value,
                                               tag=attr.tag,
                                               type=attr.type
                                               ))

    def add_attribute(self, attribute_id, asset_attribute):
        """ Adds a new attribute to the asset """
        self.producer.send_asset_attribute(attribute_id, asset_attribute)

    @property
    def references_above(self):
        """ References to above OpenFactory assets """
        query = f"SELECT VALUE, TYPE FROM assets WHERE key='{self.asset_uuid}|references_above';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        if df.empty or df['VALUE'][0].strip() == "":
            return []
        return [Asset(asset_uuid=asset_uuid.strip()) for asset_uuid in df['VALUE'][0].split(",")]

    @property
    def references_below(self):
        """ References to below OpenFactory assets """
        query = f"SELECT VALUE, TYPE FROM assets WHERE key='{self.asset_uuid}|references_below';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        if df.empty or df['VALUE'][0].strip() == "":
            return []
        return [Asset(asset_uuid=asset_uuid.strip()) for asset_uuid in df['VALUE'][0].split(",")]

    def add_reference_above(self, above_asset_reference):
        """ Adds a above-reference to the asset """
        query = f"SELECT VALUE FROM assets WHERE key='{self.asset_uuid}|references_above';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        if df.empty or df['VALUE'][0].strip() == "":
            references = above_asset_reference
        else:
            references = above_asset_reference + ', ' + df['VALUE'][0]

        # set the new references_above attribute
        self.producer.send_asset_attribute('references_above',
                                           AssetAttribute(
                                               value=references,
                                               tag='AssetsReferences',
                                               type='OpenFactory'
                                               ))

    def add_reference_below(self, below_asset_reference):
        """ Adds a below-reference to the asset """
        query = f"SELECT VALUE FROM assets WHERE key='{self.asset_uuid}|references_below';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        if df.empty or df['VALUE'][0].strip() == "":
            references = below_asset_reference
        else:
            references = below_asset_reference + ', ' + df['VALUE'][0]

        # set the new references_below attribute
        self.producer.send_asset_attribute('references_below',
                                           AssetAttribute(
                                               value=references,
                                               tag='AssetsReferences',
                                               type='OpenFactory'
                                               ))

    def wait_until(self, attribute, value, kafka_group_id=None):
        """ Waits until the asset attribute has a specific value """

        if self.__getattr__(attribute).value == value:
            return

        if kafka_group_id is None:
            kafka_group_id = f"{self.asset_uuid}_{uuid.uuid4()}"

        consumer = KafkaAssetConsumer(
            consumer_group_id=kafka_group_id,
            asset_uuid=self.asset_uuid,
            on_message=None,
            bootstrap_servers=self.bootstrap_servers,
            ksqldb_url=self.ksqldb_url)

        while True:
            msg = consumer.consumer.poll(timeout=0.1)
            if msg is None:
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(f"Error: {msg.error()}")
                    break

            # Decode the message
            msg_key = msg.key().decode('utf-8') if msg.key() else None
            msg_value = json.loads(msg.value().decode('utf-8'))
            msg_value = CaseInsensitiveDict(msg_value)

            # Filter desired key
            if msg_key != self.asset_uuid:
                continue

            if msg_value['id'] == attribute:
                if msg_value['type'] == 'Samples' and msg_value['value'] != 'UNAVAILABLE':
                    if float(msg_value['value']) == value:
                        break
                else:
                    if msg_value['value'] == value:
                        break

        consumer.consumer.close()

    def __consume_samples(self, topic, kakfa_group_id, on_sample):
        """ Kafka consumer that runs in a separate thread and calls `on_sample` """

        class SamplesConsumer(KafkaAssetConsumer):

            def filter_messages(self, msg_value):
                """ Filters out Samples """
                return msg_value if msg_value['type'] == 'Samples' else None

        self._samples_consumer_instance = SamplesConsumer(
            consumer_group_id=kakfa_group_id,
            asset_uuid=self.asset_uuid,
            on_message=on_sample,
            bootstrap_servers=self.bootstrap_servers,
            ksqldb_url=self.ksqldb_url)
        self._samples_consumer_instance.consume()

    def subscribe_to_samples(self, on_sample, kakfa_group_id):
        """ Subscribe to samples messages of the Asset """
        self._samples_consumer_thread = threading.Thread(
            target=self.__consume_samples,
            args=(self.ksql.get_kafka_topic('ASSETS_STREAM'), kakfa_group_id, on_sample),
            daemon=True
        )
        self._samples_consumer_thread.start()
        return self._samples_consumer_thread

    def stop_samples_subscription(self):
        """ Stop the Kafka consumer gracefully """
        if hasattr(self, "_samples_consumer_instance"):
            self._samples_consumer_instance.stop()
        if hasattr(self, "_samples_consumer_thread"):
            self._samples_consumer_thread.join()

    def __consume_events(self, topic, kakfa_group_id, on_event):
        """ Kafka consumer that runs in a separate thread and calls `on_event` """

        class EventsConsumer(KafkaAssetConsumer):

            def filter_messages(self, msg_value):
                """ Filters out Events """
                return msg_value if msg_value['type'] == 'Events' else None

        self._events_consumer_instance = EventsConsumer(
            consumer_group_id=kakfa_group_id,
            asset_uuid=self.asset_uuid,
            on_message=on_event,
            bootstrap_servers=self.bootstrap_servers,
            ksqldb_url=self.ksqldb_url)
        self._events_consumer_instance.consume()

    def subscribe_to_events(self, on_event, kakfa_group_id):
        """ Subscribe to events messages of the Asset """
        self._events_consumer_thread = threading.Thread(
            target=self.__consume_events,
            args=(self.ksql.get_kafka_topic('ASSETS_STREAM'), kakfa_group_id, on_event),
            daemon=True
        )
        self._events_consumer_thread.start()
        return self._events_consumer_thread

    def stop_events_subscription(self):
        """ Stop the Kafka consumer gracefully """
        if hasattr(self, "_events_consumer_instance"):
            self._events_consumer_instance.stop()
        if hasattr(self, "_events_consumer_thread"):
            self._events_consumer_thread.join()

    def __consume_conditions(self, topic, kakfa_group_id, on_condition):
        """ Kafka consumer that runs in a separate thread and calls `on_condition` """

        class ConditionsConsumer(KafkaAssetConsumer):

            def filter_messages(self, msg_value):
                """ Filters out Conditions """
                return msg_value if msg_value['type'] == 'Condition' else None

        self._conditions_consumer_instance = ConditionsConsumer(
            consumer_group_id=kakfa_group_id,
            asset_uuid=self.asset_uuid,
            on_message=on_condition,
            bootstrap_servers=self.bootstrap_servers,
            ksqldb_url=self.ksqldb_url)
        self._conditions_consumer_instance.consume()

    def subscribe_to_conditions(self, on_condition, kakfa_group_id):
        """ Subscribe to conditions messages of the Asset """
        self._conditions_consumer_thread = threading.Thread(
            target=self.__consume_conditions,
            args=(self.ksql.get_kafka_topic('ASSETS_STREAM'), kakfa_group_id, on_condition),
            daemon=True
        )
        self._conditions_consumer_thread.start()
        return self._conditions_consumer_thread

    def stop_conditions_subscription(self):
        """ Stop the Kafka consumer gracefully """
        if hasattr(self, "_conditions_consumer_instance"):
            self._conditions_consumer_instance.stop()
        if hasattr(self, "_conditions_consumer_thread"):
            self._conditions_consumer_thread.join()


if __name__ == "__main__":

    # Example usage of Asset
    cnc = Asset('PROVER3018')

    # list samples
    print(cnc.samples())
    print(cnc.Zact.value)
    print(cnc.Zact.type)
    print(cnc.Zact.timestamp)

    # redfine some values
    cnc.Zact = 10.0
    print(cnc.Zact.value)

    # subscriptions
    def on_sample(msg_key, msg_value):
        """ Callback to process received samples """
        print(f"[Sample] [{msg_key}] {msg_value}")

    def on_event(msg_key, msg_value):
        """ Callback to process received events """
        print(f"[Event] [{msg_key}] {msg_value}")

    def on_condition(msg_key, msg_value):
        """ Callback to process received conditions """
        print(f"[Condition] [{msg_key}] {msg_value}")

    cnc.subscribe_to_samples(on_sample, 'demo_samples_group')
    cnc.subscribe_to_events(on_event, 'demo_events_group')
    cnc.subscribe_to_conditions(on_condition, 'demo_conditions_group')

    # run a main loop while subscriptions remain
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping consumer threads ...")
        cnc.stop_samples_subscription()
        cnc.stop_events_subscription()
        cnc.stop_conditions_subscription()
        print("Consumers stopped")
