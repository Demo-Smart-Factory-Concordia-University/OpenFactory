import json
import threading
from confluent_kafka import Consumer, KafkaError
import openfactory.config as config
from openfactory.kafka import CaseInsensitiveDict


class KafkaCommandsConsumer:
    """
    Kafka consumer for OpenFactory CMDS_STREAM

    Consumes messages meant for the Asset with UUID asset_uuid

    The method `filter_messages` can be used to further filter messages
    """

    consumer_timeout = 0.1

    def __init__(self, consumer_group_id, asset_uuid, on_command, ksqlClient, bootstrap_servers=config.KAFKA_BROKER):
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

    def filter_messages(self, msg_value):
        """ Can be redefined as needed to further filter commands """
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
                    self.on_command(msg_key, msg_value)

        except Exception as e:
            print(f"Exception in KafkaCommandsConsumer: {e}")
        finally:
            print("Closing KafkaCommandsConsumer ...")
            self.consumer.close()

    def stop(self):
        """ Signal the consumer to stop """
        self.running.clear()


if __name__ == "__main__":

    # Example usage of KafkaCommandsConsumer class
    from openfactory.kafka import KSQLDBClient
    ksql = KSQLDBClient(config.KSQLDB)

    def on_command(msg_key, msg_value):
        """ Callback to process received messages """
        print(f"[{msg_key}] {msg_value}")

    consumer = KafkaCommandsConsumer(
        consumer_group_id="demo_ofa_commands_consumer_group",
        asset_uuid="PROVER3018",
        on_command=on_command,
        ksqlClient=ksql,
        bootstrap_servers="localhost:9092"
    )

    consumer.consume()
