""" OpenFactory Assets class. """

import time
from typing import Union, List
import openfactory.config as config
from openfactory.assets.asset_base import BaseAsset
from openfactory.kafka import KafkaAssetConsumer, KSQLDBClient


class Asset(BaseAsset):
    """
    Represents an OpenFactory Asset using the ASSET_UUID as identifier.

    This class encapsulates Asset metadata and a Kafka producer responsible for sending asset data.
    It uses the ksqlDB topology based on the `ASSETS_STREAM` stream to handle Asset data.

    Attributes:
        asset_uuid (str): Unique identifier of the Asset.
        ksql (KSQLDBClient): Client for interacting with ksqlDB.
        bootstrap_servers (str): Kafka bootstrap server address.
        producer (AssetProducer): Kafka producer instance for sending Asset messages.

    Example usage:
        .. code-block:: python

            import time
            from openfactory.assets import Asset
            from openfactory.kafka import KSQLDBClient

            ksql = KSQLDBClient('http://localhost:8088')
            cnc = Asset('PROVER3018', ksqlClient=ksql)

            # list samples
            print(cnc.samples())
            print(cnc.Zact.value)
            print(cnc.Zact.type)
            print(cnc.Zact.timestamp)

            # redefine an attribute value
            cnc.Zact = 10.0
            print(cnc.Zact.value)

            # callbacks for subscriptions
            def on_messages(msg_key, msg_value):
                print(f"[Message] [{msg_key}] {msg_value}")

            def on_sample(msg_key, msg_value):
                print(f"[Sample] [{msg_key}] {msg_value}")

            def on_event(msg_key, msg_value):
                print(f"[Event] [{msg_key}] {msg_value}")

            def on_condition(msg_key, msg_value):
                print(f"[Condition] [{msg_key}] {msg_value}")

            cnc.subscribe_to_messages(on_messages, 'demo_messages_group')
            cnc.subscribe_to_samples(on_sample, 'demo_samples_group')
            cnc.subscribe_to_events(on_event, 'demo_events_group')
            cnc.subscribe_to_conditions(on_condition, 'demo_conditions_group')

            # run a main loop while subscriptions remain active
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("Stopping consumer threads ...")
                cnc.stop_messages_subscription()
                cnc.stop_samples_subscription()
                cnc.stop_events_subscription()
                cnc.stop_conditions_subscription()
                print("Consumers stopped")
            finally:
                ksql.close()
    """

    KSQL_ASSET_TABLE = 'assets'
    KSQL_ASSET_ID = 'asset_uuid'
    ASSET_CONSUMER_CLASS = KafkaAssetConsumer

    def __init__(self, asset_uuid, ksqlClient, bootstrap_servers=config.KAFKA_BROKER):
        """
        Initializes the Asset with metadata and a Kafka producer.

        Args:
            asset_uuid (str): UUID identifier of the asset.
            ksqlClient (KSQLDBClient): Client for interacting with ksqlDB.
            bootstrap_servers (str): Kafka bootstrap server address. Defaults to config setting.
        """
        object.__setattr__(self, 'ASSET_ID', asset_uuid)
        super().__init__(ksqlClient, bootstrap_servers)

    @property
    def asset_uuid(self) -> str:
        """
        Returns the asset UUID based on runtime state.

        Returns:
            str: The asset's UUID.
        """
        return self.ASSET_ID

    def _get_reference_list(self, direction: str, as_assets: bool = False) -> List[Union[str, 'Asset']]:
        """
        Retrieves a list of asset references (UUIDs or AssetUNS objects) in the given direction.

        Args:
            direction (str): Either 'above' or 'below', indicating reference direction.
            as_assets (bool): If True, returns AssetUNS instances instead of UUID strings.

        Returns:
            List: List of asset UUIDs or AssetUNS objects.
        """
        key = f"{self.asset_uuid}|references_{direction}"
        query = f"SELECT VALUE FROM assets WHERE key='{key}';"
        df = self.ksql.query(query)

        if df.empty or not df['VALUE'][0].strip():
            return []

        uuids = [uuid.strip() for uuid in df['VALUE'][0].split(",")]
        if as_assets:
            return [Asset(asset_uuid=uuid, ksqlClient=self.ksql) for uuid in uuids]
        return uuids


if __name__ == "__main__":

    # Example usage of Asset
    ksql = KSQLDBClient(config.KSQLDB_URL)
    cnc = Asset('PROVER3018', ksqlClient=ksql)

    # list samples
    print(cnc.samples())
    print(cnc.Zact.value)
    print(cnc.Zact.type)
    print(cnc.Zact.timestamp)

    # redefine some values
    cnc.Zact = 10.0
    print(cnc.Zact.value)

    # subscriptions
    def on_messages(msg_key, msg_value):
        """ Callback to process received messages. """
        print(f"[Message] [{msg_key}] {msg_value}")

    def on_sample(msg_key, msg_value):
        """ Callback to process received samples. """
        print(f"[Sample] [{msg_key}] {msg_value}")

    def on_event(msg_key, msg_value):
        """ Callback to process received events. """
        print(f"[Event] [{msg_key}] {msg_value}")

    def on_condition(msg_key, msg_value):
        """ Callback to process received conditions. """
        print(f"[Condition] [{msg_key}] {msg_value}")

    cnc.subscribe_to_messages(on_messages, 'demo_messages_group')
    cnc.subscribe_to_samples(on_sample, 'demo_samples_group')
    cnc.subscribe_to_events(on_event, 'demo_events_group')
    cnc.subscribe_to_conditions(on_condition, 'demo_conditions_group')

    # run a main loop while subscriptions remain active
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping consumer threads ...")
        cnc.stop_messages_subscription()
        cnc.stop_samples_subscription()
        cnc.stop_events_subscription()
        cnc.stop_conditions_subscription()
        print("Consumers stopped")
    finally:
        ksql.close()
        print("Closed conection to ksqlDB server")
