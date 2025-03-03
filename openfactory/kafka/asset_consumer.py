import hashlib
import json
from confluent_kafka import Consumer, KafkaError, TopicPartition
from pyksql.ksql import KSQL
import openfactory.config as config


def get_partition_for_key(key, num_partitions):
    """ Calculate the partition number for a given key """
    return int(hashlib.md5(key.encode('utf-8')).hexdigest(), 16) % num_partitions


class KafkaAssetConsumer:
    """
    Kafka consumer for OpenFactory ASSETS_STREAM

    Consumes messages for an Asset with UUID asset_uuid

    The method `filter_messages` can be used to further filter messages
    """

    consumer_timeout = 0.1

    def __init__(self, consumer_group_id, asset_uuid, on_message, bootstrap_servers=config.KAFKA_BROKER, ksqldb_url=config.KSQLDB):
        self.ksql = KSQL(ksqldb_url)
        self.topic = self.ksql.get_kafka_topic('ASSETS_STREAM')
        self.bootstrap_servers = bootstrap_servers
        self.group_id = consumer_group_id
        self.key = asset_uuid
        self.on_message = on_message
        self.consumer = Consumer({
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': self.group_id,
            'auto.offset.reset': 'latest',
        })
        self.consumer.subscribe([self.topic],
                                on_assign=self.__on_partitions_assigned,
                                on_revoke=self.__on_partitions_revoked)

    def filter_messages(self, msg_value):
        """ Can be redefined as needed to further filter messages """
        return msg_value

    def __on_partitions_assigned(self, consumer, partitions):
        """ Callback when partitions are assigned to this consumer """
        # When partitions are assigned, manually calculate partition for the key
        num_partitions = len(partitions)
        partition = get_partition_for_key(self.key, num_partitions)
        print(f"Partitions assigned: {partitions}. Consuming from partition {partition}.")

        # Assign the consumer to the calculated partition
        consumer.assign([TopicPartition(self.topic, partition)])

    def __on_partitions_revoked(self, consumer, partitions):
        """ Callback when partitions are revoked from this consumer """
        print(f"Partitions revoked: {partitions}. Need to reassign partitions.")

        # TO-DO: need to implement logic for cleanup or offset commits if necessary

    def consume(self):
        """ Consume messages """
        try:
            while True:
                msg = self.consumer.poll(timeout=self.consumer_timeout)
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

                # Filter desired key
                if msg_key != self.key:
                    continue

                # Apply additional filter
                msg_value = self.filter_messages(msg_value)

                if msg_value:
                    self.on_message(msg_key, msg_value)

        except KeyboardInterrupt:
            print("Stopping consumer...")
        finally:
            self.consumer.close()


if __name__ == "__main__":

    # Example usage of the KafkaAssetConsumer

    def on_message(msg_key, msg_value):
        """ Callback to process received messages """
        print(f"[{msg_key}] {msg_value}")

    class PROVER3018_EventsConsumer(KafkaAssetConsumer):

        def filter_messages(self, msg_value):
            """ Filters out Events """
            if msg_value['type'] == 'Events':
                return msg_value
            else:
                return None

    consumer = PROVER3018_EventsConsumer(
        consumer_group_id="demo_ofa_assets_consumer_group",
        asset_uuid="PROVER3018",
        on_message=on_message,
        bootstrap_servers="localhost:9092"
    )

    consumer.consume()
