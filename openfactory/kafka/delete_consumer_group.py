from kafka.admin import KafkaAdminClient
import openfactory.config as config


def delete_consumer_group(kafka_group_id, bootstrap_servers=config.KAFKA_BROKER):
    """
    Delete Kafka consumer group
    """
    admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
    try:
        admin_client.delete_consumer_groups([kafka_group_id])
        print(f"Consumer group {kafka_group_id} deleted")
    except Exception as e:
        print(f"Error deleting consumer group {kafka_group_id}: {e}")
