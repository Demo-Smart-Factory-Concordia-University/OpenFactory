""" OpenFactory Kafka module. """

from kafka.admin import KafkaAdminClient
from openfactory.kafka.case_insensitive_dict import CaseInsensitiveDict
from openfactory.kafka.asset_consumer import KafkaAssetConsumer
from openfactory.kafka.asset_uns_consumer import KafkaAssetUNSConsumer
from openfactory.kafka.commands_consumer import KafkaCommandsConsumer
from openfactory.kafka.asset_producer import AssetProducer
from openfactory.kafka.ksql import KSQLDBClient
from openfactory.kafka.kafka_logger import kafka_logger
import openfactory.config as config


def delete_consumer_group(kafka_group_id: str, bootstrap_servers: str = config.KAFKA_BROKER) -> None:
    """
    Delete a Kafka consumer group by ID.

    This uses the Kafka Admin API to attempt deletion of the specified consumer group.

    Args:
        kafka_group_id (str): The ID of the Kafka consumer group to delete.
        bootstrap_servers (str): Kafka bootstrap server(s) to connect to.

    Raises:
        Exception: For unexpected errors during deletion.
    """
    admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
    try:
        admin_client.delete_consumer_groups([kafka_group_id])
        kafka_logger.info(f"Consumer group {kafka_group_id} deleted")
    except Exception as e:
        kafka_logger.error(f"Error deleting consumer group {kafka_group_id}: {e}")
