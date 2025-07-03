""" Kafka consumer for the OpenFactory stream ASSETS_STREAM. """

import json
import threading
import traceback
from confluent_kafka import Consumer, KafkaError
from openfactory.kafka.case_insensitive_dict import CaseInsensitiveDict
import openfactory.config as config
from openfactory.kafka.ksql import KSQLDBClient
from openfactory.kafka.kafka_logger import kafka_logger


class KafkaAssetConsumer:
    """
    Kafka consumer for OpenFactory's ASSETS_STREAM.

    Consumes messages for an Asset with UUID asset_uuid
    Messages are filtered by key, and optionally via the `filter_messages` method.

    Example usage:
        .. code-block:: python

            from openfactory.kafka import KafkaAssetConsumer, KSQLDBClient

            def on_message(msg_key, msg_value):
                print(f"[{msg_key}] {msg_value}")

            class PROVER3018_EventsConsumer(KafkaAssetConsumer):

                def filter_messages(self, msg_value):
                    # filter Events messages
                    if msg_value['type'] == 'Events':
                        return msg_value
                    else:
                        return None

            consumer = PROVER3018_EventsConsumer(
                asset_uuid="PROVER3018",
                consumer_group_id="demo_ofa_assets_consumer_group",
                on_message=on_message,
                ksqlClient=KSQLDBClient('http://localhost:8088'),
                bootstrap_servers="localhost:9092"
            )

            consumer.consume()
    """

    consumer_timeout = 0.1
    KSQL_ASSET_STREAM = 'ASSETS_STREAM'

    def __init__(
        self,
        asset_uuid: str,
        consumer_group_id: str,
        on_message: callable,
        ksqlClient: KSQLDBClient,
        bootstrap_servers: str = config.KAFKA_BROKER
    ):
        """
        Initialize the Kafka consumer.

        Args:
            asset_uuid (str): UUID of the asset to filter messages by.
            consumer_group_id (str): Kafka consumer group ID.
            on_message (Callable): Callback to process each valid message.
            ksqlClient (KSQLDBClient): Client object to get Kafka topic information.
            bootstrap_servers (str): Kafka bootstrap servers (default from config).
        """
        self.ksql = ksqlClient
        self.topic = self.ksql.get_kafka_topic(self.KSQL_ASSET_STREAM)
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

    def filter_messages(self, msg_value: dict) -> dict:
        """
        Optional filter hook to refine messages before processing.

        Can be overridden in subclasses to apply custom filtering logic.

        Args:
            msg_value (dict): The parsed Kafka message value.

        Returns:
            dict: The (possibly filtered) message value.
        """
        return msg_value

    def consume(self) -> None:
        """
        Start consuming messages from the Kafka topic.

        Polls for new messages, applies key and value filtering, and dispatches
        valid messages to the `on_message` callback.

        Raises:
            json.JSONDecodeError: If a message value is not valid JSON.
            Exception: For any other unexpected errors during consumption.
        """
        kafka_logger.info(f"Starting consuming messages for asset {self.key}")
        try:
            while self.running.is_set():
                msg = self.consumer.poll(timeout=self.consumer_timeout)
                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        kafka_logger.error(f"Error: {msg.error()}")
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
                    kafka_logger.debug(f"[{msg_key}] {msg_value}")
                    self.on_message(msg_key, msg_value)

        except json.JSONDecodeError as e:
            kafka_logger.error(f"Topic contained a none JSON value: {e} - raw: {msg.value().decode('utf-8')}")
        except Exception as e:
            print(f"Exception in KafkaAssetConsumer: {e}")
            traceback.print_exc()
        finally:
            kafka_logger.info("Closing KafkaAssetConsumer ...")
            self.consumer.close()

    def stop(self) -> None:
        """ Signal the consumer to stop. """
        self.running.clear()


if __name__ == "__main__":
    """
    Example usage of KafkaAssetConsumer for processing asset-related events.

    This example demonstrates how to:
    - Instantiate the KafkaAssetConsumer class with a custom asset UUID.
    - Create a subclass of KafkaAssetConsumer (`PROVER3018_EventsConsumer`) to filter out specific messages.
    - Use a custom callback (`on_message`) to handle the messages.
    - Consume Kafka messages related to the asset `PROVER3018` using the configured consumer.

    To run the example:
        python openfactory/kafka/asset_consumer.py
    """
    kafka_logger.level = 'INFO'
    ksql = KSQLDBClient(config.KSQLDB_URL)

    def on_message(msg_key, msg_value):
        """ Callback to process received messages. """
        print(f"[{msg_key}] {msg_value}")

    class PROVER3018_EventsConsumer(KafkaAssetConsumer):
        """ Example KafkaAssetConsumer. """

        def filter_messages(self, msg_value):
            """ Filters out Events. """
            if msg_value['type'] == 'Events':
                return msg_value
            else:
                return None

    consumer = PROVER3018_EventsConsumer(
        asset_uuid="PROVER3018",
        consumer_group_id="demo_ofa_assets_consumer_group",
        on_message=on_message,
        ksqlClient=ksql,
        bootstrap_servers="localhost:9092"
    )

    consumer.consume()
