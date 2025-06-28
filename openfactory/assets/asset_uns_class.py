""" OpenFactory AssetUNS class. """

from typing import Union, List
import openfactory.config as config
from openfactory.assets.asset_base import BaseAsset
from openfactory.kafka import KafkaAssetUNSConsumer


class AssetUNS(BaseAsset):
    """
    Represents an OpenFactory asset using the UNS identifier.

    This class encapsulates asset metadata and a Kafka producer responsible for sending asset data.
    It uses the ksqlDB topology based on the ASSETS_STREAM_UNS stream to handle asset data.

    Attributes:
        KSQL_ASSET_TABLE (str): Name of ksqlDB table of asset states (`assets_uns`)
        KSQL_ASSET_ID (str): ksqlDB ID used to identify the asset (`uns_id`) in the KSQL_ASSET_TABLE
        ASSET_ID (str): value of the identifer of the asset (uns_id) used in the KSQL_ASSET_TABLE
        ksql (KSQLDBClient): Client for interacting with ksqlDB.
        bootstrap_servers (str): Kafka bootstrap server address.
        ASSET_CONSUMER_CLASS (KafkaAssetUNSConsumer): Kafka consumer class for reading messages from Asset strean.
        producer (AssetProducer): Kafka producer instance for sending asset messages.

    Example usage:
    ```python
    import time
    from openfactory.assets import AssetUNS
    from openfactory.kafka import KSQLDBClient

    ksql = KSQLDBClient('http://localhost:8088')
    cnc = AssetUNS('cnc-003', ksqlClient=ksql)

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

    KSQL_ASSET_TABLE = 'assets_uns'
    KSQL_ASSET_ID = 'uns_id'
    ASSET_CONSUMER_CLASS = KafkaAssetUNSConsumer

    def __init__(self, uns_id, ksqlClient, bootstrap_servers=config.KAFKA_BROKER):
        """
        Initializes the Asset with metadata and a Kafka producer.

        Args:
            uns_id (str): UNS identifier of the asset.
            ksqlClient (KSQLDBClient): Client for interacting with ksqlDB.
            bootstrap_servers (str): Kafka bootstrap server address. Defaults to config setting.
        """
        object.__setattr__(self, 'ASSET_ID', uns_id)
        super().__init__(ksqlClient, bootstrap_servers)

    @property
    def asset_uuid(self) -> str:
        """
        Returns the asset UUID based on runtime state.

        Returns:
            str: The asset's UUID.
        """
        query = f"SELECT asset_uuid FROM asset_to_uns_map WHERE {self.KSQL_ASSET_ID}='{self.ASSET_ID}';"
        df = self.ksql.query(query)
        if df.empty:
            return None
        return df['ASSET_UUID'][0]

    def _get_reference_list(self, direction: str, as_assets: bool = False) -> List[Union[str, 'AssetUNS']]:
        """
        Retrieves a list of asset references (UUIDs or AssetUNS objects) in the given direction.

        Args:
            direction (str): Either 'above' or 'below', indicating reference direction.
            as_assets (bool): If True, returns AssetUNS instances instead of UUID strings.

        Returns:
            List: List of asset UUIDs or AssetUNS objects.
        """
        key = f"{self.ASSET_ID}|references_{direction}"
        query = f"SELECT VALUE FROM {self.KSQL_ASSET_TABLE} WHERE key='{key}';"
        df = self.ksql.query(query)

        if df.empty or not df['VALUE'][0].strip():
            return []

        uns_ids = [uns_id.strip() for uns_id in df['VALUE'][0].split(",")]
        if as_assets:
            return [AssetUNS(uns_id, ksqlClient=self.ksql) for uns_id in uns_ids]
        return uns_ids
