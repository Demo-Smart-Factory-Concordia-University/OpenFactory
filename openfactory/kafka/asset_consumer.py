import json
import threading
from confluent_kafka import Consumer, KafkaError
from openfactory.kafka import CaseInsensitiveDict
import openfactory.config as config


class KafkaAssetConsumer:
    """
    Kafka consumer for OpenFactory ASSETS_STREAM

    Consumes messages for an Asset with UUID asset_uuid

    The method `filter_messages` can be used to further filter messages
    """

    consumer_timeout = 0.1

    def __init__(self, consumer_group_id, asset_uuid, on_message, ksqlClient, bootstrap_servers=config.KAFKA_BROKER):
        self.ksql = ksqlClient
        self.topic = self.ksql.get_kafka_topic('ASSETS_STREAM')
        self.bootstrap_servers = bootstrap_servers
        self.group_id = consumer_group_id
        self.key = asset_uuid
        self.on_message = on_message
        self.running = threading.Event()
        self.running.set()

        self.consumer = Consumer({
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': self.group_id,
            'auto.offset.reset': 'latest',
        })
        self.consumer.subscribe([self.topic])

    def filter_messages(self, msg_value):
        """ Can be redefined as needed to further filter messages """
        return msg_value

    def consume(self):
        """ Consume messages """
        try:
            while self.running.is_set():
                msg = self.consumer.poll(timeout=self.consumer_timeout)
                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        print(f"Error: {msg.error()}")
                        break

                # Decode the message and filter key
                msg_key = msg.key().decode('utf-8') if msg.key() else None
                if msg_key != self.key:
                    continue
                msg_value = json.loads(msg.value().decode('utf-8'))
                msg_value = CaseInsensitiveDict(msg_value)

                # Apply additional filter
                msg_value = self.filter_messages(msg_value)

                if msg_value:
                    self.on_message(msg_key, msg_value)

        except json.JSONDecodeError as e:
            print(f"Topic contained a none JSON value: {e} - raw: {msg.value().decode('utf-8')}")
        except Exception as e:
            print(f"Exception in KafkaAssetConsumer: {e}")
        finally:
            print("Closing KafkaAssetConsumer ...")
            self.consumer.close()

    def stop(self):
        """ Signal the consumer to stop """
        self.running.clear()


if __name__ == "__main__":

    # Example usage of the KafkaAssetConsumer
    from openfactory.kafka import KSQLDBClient
    ksql = KSQLDBClient(config.KSQLDB)

    def on_message(msg_key, msg_value):
        """ Callback to process received messages """
        print(f"[{msg_key}] {msg_value}")

    class PROVER3018_EventsConsumer(KafkaAssetConsumer):

        def filter_messages(self, msg_value):
            """ Filters out Events """
            print(msg_value)
            if msg_value['type'] == 'Events':
                return msg_value
            else:
                return None

    consumer = PROVER3018_EventsConsumer(
        consumer_group_id="demo_ofa_assets_consumer_group",
        asset_uuid="PROVER3018",
        on_message=on_message,
        ksqlClient=ksql,
        bootstrap_servers="localhost:9092"
    )

    consumer.consume()
