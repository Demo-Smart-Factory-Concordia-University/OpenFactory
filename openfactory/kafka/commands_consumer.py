""" Kafka consumer for OpenFactory's CMDS_STREAM. """

import json
import threading
from typing import Dict
from confluent_kafka import Consumer, KafkaError
import openfactory.config as config
from openfactory.kafka import CaseInsensitiveDict
from openfactory.kafka.ksql import KSQLDBClient
from openfactory.kafka.kafka_logger import kafka_logger


class KafkaCommandsConsumer:
    """
    Kafka consumer for OpenFactory CMDS_STREAM.

    Consumes command messages intended for a specific asset identified by `asset_uuid`.
    A user-provided callback (`on_command`) is called when a valid message is received.
    You can override `filter_messages` to apply custom filtering on received messages.

    Example usage:
        .. code-block:: python

            from openfactory.kafka import KafkaCommandsConsumer, KSQLDBClient

            def on_command(msg_key, msg_value):
                # Callback to process received messages.
                print(f"[{msg_key}] {msg_value}")

            consumer = KafkaCommandsConsumer(
                consumer_group_id="demo_ofa_commands_consumer_group",
                asset_uuid="PROVER3018",
                on_command=on_command,
                ksqlClient=KSQLDBClient('http://localhost:8088'),
                bootstrap_servers="localhost:9092"
            )

            consumer.consume()
    """

    consumer_timeout = 0.1

    def __init__(
        self,
        consumer_group_id: str,
        asset_uuid: str,
        on_command: callable,
        ksqlClient: KSQLDBClient,
        bootstrap_servers: str = config.KAFKA_BROKER
    ):
        """
        Initialize the KafkaCommandsConsumer.

        Args:
            consumer_group_id (str): Kafka consumer group ID.
            asset_uuid (str): UUID of the asset to filter messages for.
            on_command (Callable): Callback to process valid messages.
            ksqlClient (KSQLDBClient): Client to retrieve Kafka topic metadata.
            bootstrap_servers (str): Kafka broker address.
        """
        self.ksql = ksqlClient
        self.topic = self.ksql.get_kafka_topic('CMDS_STREAM')
        self.bootstrap_servers = bootstrap_servers
        self.group_id = consumer_group_id
        self.key = asset_uuid
        self.on_command = on_command
        self.running = threading.Event()
        self.running.set()
        self.consumer = Consumer({
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': self.group_id,
            'auto.offset.reset': 'latest',
        })
        self.consumer.subscribe([self.topic])

    def filter_messages(self, msg_value: Dict) -> Dict:
        """
        Optional message filter method.

        Override this method to filter or transform command messages before they
        are passed to the `on_command` callback.

        Args:
            msg_value (dict): The incoming message value as a dictionary.

        Returns:
            dict or None: The message value to process, or None to discard it.
        """
        return msg_value

    def consume(self) -> None:
        """
        Start consuming messages from Kafka.

        This method runs a loop, polling the Kafka topic for new messages,
        filtering them by key and (optionally) content, and dispatching
        them to the `on_command` callback.

        Raises:
            json.JSONDecodeError: If a message is not valid JSON.
            Exception: For all other runtime errors during consumption.
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

                # Decode the message
                msg_key = msg.key().decode('utf-8') if msg.key() else None
                msg_value = json.loads(msg.value().decode('utf-8'))
                msg_value = CaseInsensitiveDict(msg_value)

                # Filter desired key
                if msg_key != self.key:
                    continue

                # Apply additional filter
                msg_value = self.filter_messages(msg_value)

                if msg_value:
                    kafka_logger.debug(f"[{msg_key}] {msg_value}")
                    self.on_command(msg_key, msg_value)

        except json.JSONDecodeError as e:
            kafka_logger.error(f"Commands topic contained a none JSON value: {e} - raw: {msg.value().decode('utf-8')}")
        except Exception as e:
            print(f"Exception in KafkaCommandsConsumer: {e}")
        finally:
            kafka_logger.info("Closing KafkaCommandsConsumer ...")
            self.consumer.close()

    def stop(self) -> None:
        """ Signal the consumer to stop. """
        self.running.clear()


if __name__ == "__main__":

    # Example usage of KafkaCommandsConsumer class
    kafka_logger.level = 'INFO'
    ksql = KSQLDBClient(config.KSQLDB_URL)

    def on_command(msg_key, msg_value):
        """ Callback to process received messages. """
        print(f"[{msg_key}] {msg_value}")

    consumer = KafkaCommandsConsumer(
        consumer_group_id="demo_ofa_commands_consumer_group",
        asset_uuid="PROVER3018",
        on_command=on_command,
        ksqlClient=ksql,
        bootstrap_servers="localhost:9092"
    )

    consumer.consume()
