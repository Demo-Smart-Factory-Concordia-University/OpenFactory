""" OpenFactory Assets Kafka Producers / Consumers. """

import json
from confluent_kafka import Producer
from typing import Union, Optional
from openfactory.kafka import KSQLDBClient, KafkaAssetConsumer
from openfactory.assets.utils import AssetAttribute
import openfactory.config as config


class AssetProducer(Producer):
    """
    Kafka producer for sending OpenFactory asset data.

    This class wraps a Kafka producer and binds it to a specific asset and topic used by OpenFactory.

    Attributes:
        ksql (KSQLDBClient): Client used to interact with ksqlDB.
        topic (str): Kafka topic to which asset data will be produced.
        asset_uuid (str): Unique identifier of the asset being tracked.
    """

    def __init__(self, asset_uuid: str, ksqlClient: KSQLDBClient, bootstrap_servers: str = config.KAFKA_BROKER) -> None:
        """
        Initializes the AssetProducer.

        Args:
            asset_uuid (str): UUID of the asset this producer is associated with.
            ksqlClient (KSQLDBClient): Client to retrieve Kafka topic info, typically a wrapper over ksqlDB.
            bootstrap_servers (str): Kafka bootstrap server address, defaults to value from config.
        """
        super().__init__({'bootstrap.servers': bootstrap_servers})
        self.ksql = ksqlClient
        self.topic = self.ksql.get_kafka_topic('ASSETS_STREAM')
        self.asset_uuid = asset_uuid

    def send_asset_attribute(self, assetID: Union[str, int], assetAttribute: AssetAttribute) -> None:
        """
        Sends a Kafka message representing an asset attribute.

        Constructs a JSON message from the given asset attribute and sends it to the Kafka ASSETS_STREAM topic.

        Args:
            assetID (Union[str, int]): The unique identifier for the asset instance.
            assetAttribute (AssetAttribute): The asset attribute object containing value, type, tag, and timestamp.
        """
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


class TypedKafkaConsumer(KafkaAssetConsumer):
    """
    Kafka consumer that filters messages based on a specific expected type.

    This subclass of `KafkaAssetConsumer` adds filtering capability by inspecting
    the 'type' field of incoming messages. If an expected type is provided, only
    messages matching that type will be passed through; otherwise, all messages
    are accepted.
    """

    def __init__(self, expected_type: Optional[str], *args, **kwargs):
        """
        Initializes the TypedKafkaConsumer.

        Args:
            expected_type (Optional[str]): The message type to filter for ('Samples', 'Events', 'Conditions').
                                           If None, no filtering is applied.
            *args: Positional arguments passed to the base KafkaAssetConsumer.
            **kwargs: Keyword arguments passed to the base KafkaAssetConsumer.
        """
        self.expected_type = expected_type
        super().__init__(*args, **kwargs)

    def filter_messages(self, msg_value):
        """
        Filters Kafka messages based on the expected type.

        Args:
            msg_value (dict): The Kafka message value to filter.

        Returns:
            dict or None: The message if it matches the expected type or if no type filtering is applied;
                          otherwise, returns None to discard the message.
        """
        if not self.expected_type:
            return msg_value
        return msg_value if msg_value.get('type') == self.expected_type else None
