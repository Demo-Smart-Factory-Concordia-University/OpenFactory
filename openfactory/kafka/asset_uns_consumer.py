""" Kafka consumer for the OpenFactory  stream ASSETS_STREAM_UNS. """

from openfactory.kafka import KafkaAssetConsumer
import openfactory.config as config


class KafkaAssetUNSConsumer(KafkaAssetConsumer):
    """
    Kafka consumer for OpenFactory's ASSETS_STREAM_UNS.

    Consumes messages for an Asset with UNS_ID asset_uns_id
    Messages are filtered by key, and optionally via the `filter_messages` method.
    """

    KSQL_ASSET_STREAM = 'ASSETS_STREAM_UNS'

    def __init__(self, consumer_group_id, asset_uns_id, on_message, ksqlClient, bootstrap_servers=config.KAFKA_BROKER):
        """
        Initialize the Kafka consumer.

        Args:
            consumer_group_id (str): Kafka consumer group ID.
            asset_uns_id (str): UNS_ID of the asset to filter messages by.
            on_message (Callable): Callback to process each valid message.
            ksqlClient (KSQLDBClient): Client object to get Kafka topic information.
            bootstrap_servers (str): Kafka bootstrap servers (default from config).
        """
        super().__init__(consumer_group_id, asset_uns_id, on_message, ksqlClient, bootstrap_servers)


if __name__ == "__main__":
    """
    Example usage of KafkaAssetUNSConsumer for processing asset-related events.

    This example demonstrates how to:
    - Instantiate the KafkaAssetUNSConsumer class with a custom asset UNS_ID.
    - Create a subclass of KafkaAssetUNSConsumer (`CNC_EventsConsumer`) to filter out specific messages.
    - Use a custom callback (`on_message`) to handle the messages.
    - Consume Kafka messages related to the asset with UNS ID `cnc` using the configured consumer.

    To run the example:
        python openfactory/kafka/asset_uns_consumer.py
    """

    from openfactory.kafka.ksql import KSQLDBClient
    from openfactory.kafka.kafka_logger import kafka_logger

    kafka_logger.level = 'INFO'
    ksql = KSQLDBClient(config.KSQLDB_URL)

    def on_message(msg_key, msg_value):
        """ Callback to process received messages. """
        print(f"[{msg_key}] {msg_value}")

    class CNC_EventsConsumer(KafkaAssetUNSConsumer):
        """ Example KafkaAssetUNSConsumer. """

        def filter_messages(self, msg_value):
            """ Filters out Events. """
            if msg_value['type'] == 'Events':
                return msg_value
            else:
                return None

    consumer = CNC_EventsConsumer(
        consumer_group_id="demo_ofa_assets_uns_consumer_group",
        asset_uns_id="cnc",
        on_message=on_message,
        ksqlClient=ksql,
        bootstrap_servers="localhost:9092"
    )

    consumer.consume()
