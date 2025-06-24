""" OpenFactory Assets module. """

import json
import re
import threading
import uuid
import time
from confluent_kafka import Producer, KafkaError
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Union, Literal, List, Dict, Protocol, Any, Optional
import openfactory.config as config
from openfactory.kafka import KafkaAssetConsumer, CaseInsensitiveDict, delete_consumer_group, KSQLDBClient
from openfactory.exceptions import OFAException


class AssetKafkaMessagesCallback(Protocol):
    """
    Interface for a callback used to handle Kafka asset messages.

    Args:
        msg_key (str): The key of the Kafka message (the asset UUID).
        msg_value (dict): The JSON-decoded value of the Kafka message.
    """
    def __call__(self, msg_key: str, msg_value: dict) -> None:
        """ Event messages callback interface method. """
        ...


def current_timestamp() -> str:
    """
    Returns the current timestamp in OpenFactory format.

    The format is ISO 8601 with milliseconds precision and a 'Z' to indicate UTC time,
    e.g., '2025-05-04T12:34:56.789Z'.

    Returns:
        str: The current UTC timestamp formatted in OpenFactory style.
    """
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


@dataclass
class AssetAttribute:
    """
    Represents a single attribute of an asset, including its value, type, tag, and timestamp.

    Attributes:
        value (Union[str, float]): The actual value of the attribute. Can be a string or float.
        type (Literal['Samples', 'Condition', 'Events', 'Method', 'OpenFactory', 'UNAVAILABLE']):
            The category/type of the attribute, must be one of the allowed literal strings.
        tag (str): The tag or identifier associated with this attribute.
        timestamp (str): Timestamp when the attribute was recorded, in OpenFactory format.
                         Defaults to the current timestamp if not provided.
    """

    value: Union[str, float]
    type: Literal['Samples', 'Condition', 'Events', 'Method', 'OpenFactory', 'UNAVAILABLE']
    tag: str
    timestamp: str = field(default_factory=current_timestamp)

    def __post_init__(self) -> None:
        """
        Validates the type of the attribute after initialization.

        Raises:
            ValueError: If the type is not one of the allowed literal strings.
        """
        ALLOWED_TYPES = {'Samples', 'Condition', 'Events', 'Method', 'OpenFactory', 'UNAVAILABLE'}
        if self.type not in ALLOWED_TYPES:
            raise ValueError(f"Invalid type '{self.type}'. Allowed values are: {', '.join(ALLOWED_TYPES)}")


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


class Asset:
    """
    Represents an OpenFactory asset with Kafka integration.

    This class encapsulates asset metadata and a Kafka producer responsible for sending asset data.

    Attributes:
        asset_uuid (str): Unique identifier of the asset.
        ksql (KSQLDBClient): Client for interacting with ksqlDB.
        bootstrap_servers (str): Kafka bootstrap server address.
        producer (AssetProducer): Kafka producer instance for sending asset messages.

    Example usage:
    ```python
    import time
    from openfactory.assets import Asset
    from openfactory.kafka import KafkaCommandsConsumer, KSQLDBClient

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
    ```
    """

    def __init__(self, asset_uuid: str, ksqlClient: KSQLDBClient, bootstrap_servers: str = config.KAFKA_BROKER) -> None:
        """
        Initializes the Asset with metadata and a Kafka producer.

        Args:
            asset_uuid (str): UUID identifying the asset.
            ksqlClient (KSQLDBClient): Client for interacting with ksqlDB.
            bootstrap_servers (str): Kafka bootstrap server address. Defaults to config setting.
        """
        super().__setattr__('asset_uuid', asset_uuid)
        super().__setattr__('ksql', ksqlClient)
        super().__setattr__('bootstrap_servers', bootstrap_servers)
        super().__setattr__('producer', AssetProducer(asset_uuid, ksqlClient=ksqlClient, bootstrap_servers=bootstrap_servers))

    @property
    def type(self) -> Literal['Samples', 'Condition', 'Events', 'Method', 'OpenFactory', 'UNAVAILABLE']:
        """
        Retrieves the type of the asset from ksqlDB.

        Executes a SQL query to fetch the asset type. If the query returns no result,
        the method defaults to 'UNAVAILABLE'.

        Returns:
            Literal['Samples', 'Condition', 'Events', 'Method', 'OpenFactory', 'UNAVAILABLE']:
                The asset type as stored in the `assets_type` table, or 'UNAVAILABLE' if not found.
        """
        query = f"SELECT TYPE FROM assets_type WHERE ASSET_UUID='{self.asset_uuid}';"
        df = self.ksql.query(query)
        if df.empty:
            return 'UNAVAILABLE'
        return df['TYPE'][0]

    def attributes(self) -> List[str]:
        """
        Returns all non-'Method' attribute IDs associated with this asset.

        Queries the `assets` table for all attribute IDs where the asset UUID matches
        and the type is not 'Method'.

        Returns:
            List[str]: A list of attribute IDs.
        """
        query = f"SELECT ID FROM assets WHERE asset_uuid='{self.asset_uuid}' AND TYPE != 'Method';"
        df = self.ksql.query(query)
        return df.ID.tolist()

    def _get_attributes_by_type(self, attr_type: str) -> List[Dict[str, Any]]:
        """
        Generic method to get attributes from the assets table by TYPE.

        Args:
            attr_type (str): The type of the asset attribute ('Samples', 'Events', 'Condition').

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing 'ID', 'VALUE', and cleaned 'TAG'.
        """
        query = f"SELECT ID, VALUE, TAG, TYPE FROM assets WHERE ASSET_UUID='{self.asset_uuid}' AND TYPE='{attr_type}';"
        df = self.ksql.query(query)
        return [{
            "ID": row.ID,
            "VALUE": row.VALUE,
            "TAG": re.sub(r'\{.*?\}', '', row.TAG).strip()
        } for row in df.itertuples()]

    def samples(self) -> List[Dict[str, Any]]:
        """
        Returns sample-type attributes for this asset.

        Queries the `assets` table for entries where `TYPE = 'Samples'` for the asset UUID.
        Returns a dictionary mapping attribute IDs to their values.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each containing:
                - "ID" (str): The attribute ID.
                - "VALUE" (Any): The value of the sample.
                - "TAG" (str): The cleaned tag name with placeholders removed.
        """
        return self._get_attributes_by_type('Samples')

    def events(self) -> List[Dict[str, Any]]:
        """
        Returns event-type attributes for this asset.

        Queries the `assets` table for entries where `TYPE = 'Events'` for the asset UUID.
        Returns a dictionary mapping attribute IDs to their values.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each containing:
                - "ID" (str): The attribute ID.
                - "VALUE" (Any): The value of the event.
                - "TAG" (str): The cleaned tag name with placeholders removed.
        """
        return self._get_attributes_by_type('Events')

    def conditions(self) -> List[Dict[str, Any]]:
        """
        Returns condition-type attributes for this asset.

        Queries the `assets` table for entries where `TYPE = 'Condition'` for the asset UUID.
        Cleans up the `TAG` field by removing any content in curly braces.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each containing:
                - "ID" (str): The attribute ID.
                - "VALUE" (Any): The value of the condition.
                - "TAG" (str): The cleaned tag name with placeholders removed.
        """
        return self._get_attributes_by_type('Condition')

    def methods(self) -> Dict[str, Any]:
        """
        Returns method-type attributes for this asset.

        Queries the `assets` table for entries where `TYPE = 'Method'` for the asset UUID.
        Returns a dictionary mapping attribute IDs to their method values.

        Returns:
            Dict[str, Any]: A dictionary where keys are method attribute IDs and values are the corresponding method values.
        """
        query = f"SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='{self.asset_uuid}' AND TYPE='Method';"
        df = self.ksql.query(query)
        return {row.ID: row.VALUE for row in df.itertuples()}

    def method(self, method: str, args: str = "") -> None:
        """
        Requests the execution of a method for the asset by sending a command to the Kafka stream.

        Constructs a message with the provided method name and optional arguments, and sends
        it to the `CMDS_STREAM` Kafka topic for processing.

        Args:
            method (str): The name of the method to be executed.
            args (str, optional): Arguments for the method, if any. Defaults to an empty string.
        """
        msg = {
            "CMD": method,
            "ARGS": args
        }
        self.producer.produce(topic=self.ksql.get_kafka_topic('CMDS_STREAM'),
                              key=self.asset_uuid,
                              value=json.dumps(msg))
        self.producer.flush()

    def __getattr__(self, attribute_id: str) -> Any:
        """
        Allows access to samples, events, conditions, and methods as attributes.

        Dynamically retrieves asset attributes (such as samples, events, conditions, or methods) based on the
        `attribute_id` and returns them as an `AssetAttribute`. If the attribute is a method, it returns a callable function
        to execute that method.

        Args:
            attribute_id (str): The ID of the attribute being accessed (e.g., a sample, event, or condition).

        Returns:
            AssetAttribute or Callable:
                - If the attribute is a sample, event, or condition, returns an `AssetAttribute`.
                - If the attribute is a method, returns a callable method caller function.
        """
        query = f"SELECT VALUE, TYPE, TAG, TIMESTAMP FROM assets WHERE key='{self.asset_uuid}|{attribute_id}';"
        df = self.ksql.query(query)

        if df.empty:
            return AssetAttribute(value='UNAVAILABLE',
                                  type='UNAVAILABLE',
                                  tag='UNAVAILABLE',
                                  timestamp='UNAVAILABLE')

        if df['TYPE'][0] == 'Method':
            def method_caller(*args, **kwargs) -> None:
                """
                Callable method caller function.

                Args:
                    *args: Positional arguments for the method.
                    **kwargs: Keyword arguments for the method.
                """
                args_str = " ".join(map(str, args))
                return self.method(attribute_id, args_str)
            return method_caller

        ret = AssetAttribute(
            value=float(df['VALUE'][0]) if df['TYPE'][0] == 'Samples' and df['VALUE'][0] != 'UNAVAILABLE' else df['VALUE'][0],
            type=df['TYPE'][0],
            tag=df['TAG'][0],
            timestamp=df['TIMESTAMP'][0]
        )

        return ret

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Sets attributes on the Asset object and sends updates to Kafka.

        Overrides the default attribute setting behavior. If the attribute name
        exists in the asset's defined attributes (`self.attributes()`), it updates the attribute's
        value and sends the update to Kafka using the asset's producer.

        If the attribute is **not** a defined Asset attribute:
        - It is treated as a regular class attribute and set normally.
        - If the value is an instance of `AssetAttribute`, an exception is raised to prevent
        accidentally setting asset-specific attributes outside the defined schema.

        If the attribute **is** a defined Asset attribute:
        - If the value is an `AssetAttribute`, it is sent directly.
        - If the value is a raw value (e.g., int, str, etc.), it wraps the value in an
        `AssetAttribute` using the current attribute’s metadata (tag, type) and sends it.

        Args:
            name (str): The name of the attribute being set.
            value (Any): The value to assign to the attribute. This can be a raw value or an `AssetAttribute`.

        Raises:
            OFAException: If the attribute is not defined in the asset but the value is an `AssetAttribute`.

        """
        # if not an Asset attributes, handle it as a class attribute
        if name not in self.attributes():
            if isinstance(value, AssetAttribute):
                raise OFAException(f"The attribute {name} is not defined in the asset {self.asset_uuid}. Use the `add_attribute` method to define a new asset attribute.")
            super().__setattr__(name, value)
            return

        # check if value is of type AssetAttribute
        if isinstance(value, AssetAttribute):
            self.producer.send_asset_attribute(name, value)
            return

        # send kafka message
        attr = self.__getattr__(name)
        self.producer.send_asset_attribute(name,
                                           AssetAttribute(
                                               value=value,
                                               tag=attr.tag,
                                               type=attr.type
                                               ))

    def add_attribute(self, attribute_id: str, asset_attribute: AssetAttribute) -> None:
        """
        Adds a new attribute to the asset.

        Validates the attribute and then sends it to Kafka if it's a valid asset attribute.

        Args:
            attribute_id (str): The unique identifier for the asset attribute.
            asset_attribute (AssetAttribute): The attribute to be added, including its value, tag, and type.
        """
        self.producer.send_asset_attribute(attribute_id, asset_attribute)

    def references_above_uuid(self) -> List[str]:
        """
        Retrieves a list of asset UUIDs of assets above the current asset.

        Queries the `assets` table to retrieve the `VALUE` field associated with the key
        indicating the assets "above" the current one. If the `VALUE` field is empty or
        contains only whitespace, an empty list is returned.

        Returns:
            List[str]: A list of asset UUIDs (as strings) that are above the current asset.
        """
        query = f"SELECT VALUE, TYPE FROM assets WHERE key='{self.asset_uuid}|references_above';"
        df = self.ksql.query(query)
        if df.empty or df['VALUE'][0].strip() == "":
            return []
        return [item.strip() for item in df['VALUE'][0].split(',')]

    @property
    def references_above(self) -> List['Asset']:
        """
        Retrieves a list of assets above the current asset.

        Queries the `assets` table for the `VALUE` field associated with the key indicating
        the assets "above" the current one. If the `VALUE` field is empty or contains only
        whitespace, an empty list is returned. Otherwise, a list of `Asset` objects is created
        for each referenced asset.

        Returns:
            List[Asset]: A list of `Asset` objects that are above the current asset.
        """
        query = f"SELECT VALUE, TYPE FROM assets WHERE key='{self.asset_uuid}|references_above';"
        df = self.ksql.query(query)
        if df.empty or df['VALUE'][0].strip() == "":
            return []
        return [Asset(asset_uuid=asset_uuid.strip(), ksqlClient=self.ksql) for asset_uuid in df['VALUE'][0].split(",")]

    def references_below_uuid(self) -> List[str]:
        """
        Retrieves a list of asset UUIDs below the current asset.

        Queries the `assets` table for the `VALUE` field associated with the key indicating
        the assets "below" the current one. If the `VALUE` field is empty or contains only
        whitespace, an empty list is returned. Otherwise, a list of asset UUIDs is returned.

        Returns:
            List[str]: A list of asset UUIDs (as strings) that are below the current asset.
        """
        query = f"SELECT VALUE, TYPE FROM assets WHERE key='{self.asset_uuid}|references_below';"
        df = self.ksql.query(query)
        if df.empty or df['VALUE'][0].strip() == "":
            return []
        return [item.strip() for item in df['VALUE'][0].split(',')]

    @property
    def references_below(self) -> List['Asset']:
        """
        Retrieves a list of assets below the current asset.

        Queries the `assets` table for the `VALUE` field associated with the key indicating
        the assets "below" the current one. If the `VALUE` field is empty or contains only
        whitespace, an empty list is returned. Otherwise, a list of `Asset` objects is created
        for each referenced asset.

        Returns:
            List[Asset]: A list of `Asset` objects that are below the current asset.
        """
        query = f"SELECT VALUE, TYPE FROM assets WHERE key='{self.asset_uuid}|references_below';"
        df = self.ksql.query(query)
        if df.empty or df['VALUE'][0].strip() == "":
            return []
        return [Asset(asset_uuid=asset_uuid.strip(), ksqlClient=self.ksql) for asset_uuid in df['VALUE'][0].split(",")]

    def add_reference_above(self, above_asset_reference: str) -> None:
        """
        Adds a reference to an asset above the current asset.

        Queries the `assets` table to retrieve the current list of assets above the current asset.
        If there are existing references, the new reference is added to the list. Otherwise, the new reference
        becomes the only entry. The updated references are then sent to Kafka.

        Args:
            above_asset_reference (str): The asset UUID of the asset above the current one to be added.
        """
        query = f"SELECT VALUE FROM assets WHERE key='{self.asset_uuid}|references_above';"
        df = self.ksql.query(query)
        if df.empty or df['VALUE'][0].strip() == "":
            references = above_asset_reference
        else:
            references = above_asset_reference + ', ' + df['VALUE'][0]

        # set the new references_above attribute
        self.producer.send_asset_attribute('references_above',
                                           AssetAttribute(
                                               value=references,
                                               tag='AssetsReferences',
                                               type='OpenFactory'
                                               ))

    def add_reference_below(self, below_asset_reference: str) -> None:
        """
        Adds a reference to an asset below the current asset.

        Queries the `assets` table to retrieve the current list of assets below the current asset.
        If there are existing references, the new reference is added to the list. Otherwise, the new reference
        becomes the only entry. The updated references are then sent to Kafka.

        Args:
            below_asset_reference (str): The asset UUID of the asset below the current one to be added.
        """
        query = f"SELECT VALUE FROM assets WHERE key='{self.asset_uuid}|references_below';"
        df = self.ksql.query(query)
        if df.empty or df['VALUE'][0].strip() == "":
            references = below_asset_reference
        else:
            references = below_asset_reference + ', ' + df['VALUE'][0]

        # set the new references_below attribute
        self.producer.send_asset_attribute('references_below',
                                           AssetAttribute(
                                               value=references,
                                               tag='AssetsReferences',
                                               type='OpenFactory'
                                               ))

    def wait_until(self, attribute: str, value: Any, timeout: int = 30, use_ksqlDB: bool = False) -> bool:
        """
        Waits until the asset attribute has a specific value or times out.

        Monitors either the Kafka topic or ksqlDB to check if the attribute value matches the expected value.
        The method will return `True` if the value is found within the given timeout, and `False` if the timeout is reached.

        Args:
            attribute (str): The attribute of the asset to monitor.
            value (Any): The value to wait for the attribute to match.
            timeout (int, optional): The maximum time to wait, in seconds. Default is 30 seconds.
            use_ksqlDB (bool, optional): If `True`, uses ksqlDB instead of Kafka topic to check the attribute value. Default is `False`.

        Returns:
            bool: `True` if the attribute value matches the expected value within the timeout, `False` otherwise.
        """
        if self.__getattr__(attribute).value == value:
            return True

        start_time = time.time()

        if use_ksqlDB:
            while True:
                if (time.time() - start_time) > timeout:
                    return False

                if self.__getattr__(attribute).value == value:
                    return True
                time.sleep(0.1)

        kafka_group_id = f"{self.asset_uuid}_{uuid.uuid4()}"

        consumer = KafkaAssetConsumer(
            consumer_group_id=kafka_group_id,
            asset_uuid=self.asset_uuid,
            on_message=None,
            ksqlClient=self.ksql,
            bootstrap_servers=self.bootstrap_servers)

        while True:
            # Check for timeout
            if (time.time() - start_time) > timeout:
                consumer.consumer.close()
                delete_consumer_group(kafka_group_id, bootstrap_servers=self.bootstrap_servers)
                return False

            msg = consumer.consumer.poll(timeout=0.1)
            if msg is None:
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(f"Error: {msg.error()}")
                    break

            msg_key = msg.key().decode('utf-8') if msg.key() else None
            msg_value = json.loads(msg.value().decode('utf-8'))
            msg_value = CaseInsensitiveDict(msg_value)

            if msg_key != self.asset_uuid:
                continue

            if msg_value['id'] == attribute:
                if msg_value['type'] == 'Samples' and msg_value['value'] != 'UNAVAILABLE':
                    try:
                        if float(msg_value['value']) == value:
                            consumer.consumer.close()
                            delete_consumer_group(kafka_group_id, bootstrap_servers=self.bootstrap_servers)
                            return True
                    except ValueError:
                        continue
                else:
                    if msg_value['value'] == value:
                        consumer.consumer.close()
                        delete_consumer_group(kafka_group_id, bootstrap_servers=self.bootstrap_servers)
                        return True

        consumer.consumer.close()
        delete_consumer_group(kafka_group_id, bootstrap_servers=self.bootstrap_servers)
        return False

    def __start_kafka_consumer(
            self,
            consumer_key: str,
            kafka_group_id: str,
            on_message: AssetKafkaMessagesCallback,
            expected_type: Optional[str] = None
            ) -> None:
        """
        Starts a Kafka consumer for the asset and begins consuming messages.

        Initializes a `TypedKafkaConsumer` instance for the specified Kafka consumer group ID and
        message handler. If an expected message type is provided, the consumer will filter messages
        by type. The consumer instance is stored as an attribute using the provided `consumer_key`.

        Args:
            consumer_key (str): A unique identifier for the consumer (used to name internal attributes).
            kafka_group_id (str): The Kafka consumer group ID.
            on_message (AssetKafkaMessagesCallback): Callback function to process received messages.
                It should accept two arguments: `msg_key` (str) and `msg_value` (dict).
            expected_type (Optional[str]): The expected message type to filter for (e.g., "Samples").
                If None, all message types will be accepted.
        """
        consumer = TypedKafkaConsumer(
            expected_type=expected_type,
            consumer_group_id=kafka_group_id,
            asset_uuid=self.asset_uuid,
            on_message=on_message,
            ksqlClient=self.ksql,
            bootstrap_servers=self.bootstrap_servers
        )
        super().__setattr__(f"_{consumer_key}_consumer_instance", consumer)
        consumer.consume()

    def __subscribe(
            self,
            kind: str,
            on_message: AssetKafkaMessagesCallback,
            kafka_group_id: str,
            expected_type: Optional[str] = None
            ) -> threading.Thread:
        """
        Subscribes to a Kafka topic for a specific message type in a background thread.

        Creates and starts a daemon thread that runs a typed Kafka consumer.
        The thread and group ID are stored on the instance using the provided `kind`
        as part of the attribute name. The consumer filters messages by type if `expected_type` is given.

        Args:
            kind (str): A string identifier used to name internal thread and group ID attributes
                        ("samples", "events", "conditions", or "messages").
            on_message (AssetKafkaMessagesCallback): Callback function to handle incoming messages.
                Should accept two arguments: `msg_key` (str) and `msg_value` (dict).
            kafka_group_id (str): The Kafka consumer group ID used for the subscription.
            expected_type (Optional[str]): If provided, the consumer will only process messages
                where `msg_value["type"] == expected_type`.

        Returns:
            threading.Thread: The daemon thread running the Kafka consumer.
        """
        consumer_thread = threading.Thread(
            target=self.__start_kafka_consumer,
            args=(kind, kafka_group_id, on_message, expected_type),
            daemon=True
        )
        super().__setattr__(f"_{kind}_consumer_thread", consumer_thread)
        super().__setattr__(f"__{kind}_kafka_group_id", kafka_group_id)
        consumer_thread.start()
        return consumer_thread

    def __stop_subscription(self, kind: str) -> None:
        """
        Stops a Kafka consumer subscription and cleans up associated resources.

        Stops the consumer instance, joins the consumer thread, and deletes
        the corresponding Kafka consumer group. Internal attributes are looked up dynamically
        using the provided `kind` identifier.

        Args:
            kind (str): A string identifier used to locate internal consumer/thread/group ID attributes
                        ("samples", "events", "conditions", or "messages").
        """
        consumer_attr = f"_{kind}_consumer_instance"
        thread_attr = f"_{kind}_consumer_thread"
        group_id_attr = f"__{kind}_kafka_group_id"

        if hasattr(self, consumer_attr):
            getattr(self, consumer_attr).stop()
        if hasattr(self, thread_attr):
            getattr(self, thread_attr).join()
        if hasattr(self, group_id_attr):
            delete_consumer_group(
                getattr(self, group_id_attr),
                bootstrap_servers=self.bootstrap_servers
            )

    def subscribe_to_messages(self, on_message: AssetKafkaMessagesCallback, kafka_group_id: str) -> threading.Thread:
        """
        Subscribes to asset messages and starts a consumer thread.

        Initiates a Kafka consumer in a separate thread to listen for messages related to the asset.
        When a message is received, the provided `on_message` callback is called. The consumer thread runs
        as a daemon and listens for messages until stopped.

        Args:
            on_message (AssetKafkaMessagesCallback): Callable that takes (msg_key: str, msg_value: dict) and handles messages.
            kafka_group_id (str): The Kafka consumer group ID to subscribe to.

        Returns:
            threading.Thread: The thread object running the Kafka consumer.
        """
        return self.__subscribe("messages", on_message, kafka_group_id)

    def stop_messages_subscription(self) -> None:
        """
        Stops the Kafka consumer and gracefully shuts down the subscription.

        If a consumer instance exists, it is stopped and the associated consumer thread joined.
        The consumer group is deleted from Kafka to clean up the subscription.
        """
        self.__stop_subscription("messages")

    def subscribe_to_samples(self, on_sample: AssetKafkaMessagesCallback, kafka_group_id: str) -> threading.Thread:
        """
        Subscribes to 'Samples' messages and starts a consumer thread.

        Initiates a Kafka consumer in a separate thread to listen for 'Samples' messages related to the asset.
        When a 'Samples' message is received, the provided `on_sample` callback is invoked. The consumer thread
        runs as a daemon and listens for messages until stopped.

        Args:
            on_sample (AssetKafkaMessagesCallback): Callable that takes (msg_key: str, msg_value: dict) and handles samples messages.
            kafka_group_id (str): The Kafka consumer group ID to subscribe to.

        Returns:
            threading.Thread: The thread object running the Kafka consumer.
        """
        return self.__subscribe("samples", on_sample, kafka_group_id, expected_type="Samples")

    def stop_samples_subscription(self) -> None:
        """
        Stops the Kafka consumer and gracefully shuts down the subscription to 'Samples'.

        If a consumer instance exists, it is stopped, and the associated consumer thread is joined.
        The consumer group is deleted from Kafka to clean up the subscription.
        """
        self.__stop_subscription("samples")

    def subscribe_to_events(self, on_event: AssetKafkaMessagesCallback, kafka_group_id: str) -> threading.Thread:
        """
        Subscribes to 'Events' messages and starts a consumer thread.

        Initiates a Kafka consumer in a separate thread to listen for 'Events' messages related to the asset.
        When an 'Events' message is received, the provided `on_event` callback is invoked. The consumer thread
        runs as a daemon and listens for messages until stopped.

        Args:
            on_event (AssetKafkaMessagesCallback): Callable that takes (msg_key: str, msg_value: dict) and handles event messages.
            kafka_group_id (str): The Kafka consumer group ID to subscribe to.

        Returns:
            threading.Thread: The thread object running the Kafka consumer.
        """
        return self.__subscribe("events", on_event, kafka_group_id, expected_type="Events")

    def stop_events_subscription(self) -> None:
        """
        Stops the Kafka consumer and gracefully shuts down the subscription to 'Events'.

        If a consumer instance exists, it is stopped, and the associated consumer thread is joined.
        The consumer group is deleted from Kafka to clean up the subscription.
        """
        self.__stop_subscription("events")

    def subscribe_to_conditions(self, on_condition: AssetKafkaMessagesCallback, kafka_group_id: str) -> threading.Thread:
        """
        Subscribes to 'Condition' messages and starts a consumer in a separate thread.

        This method creates and starts a Kafka consumer thread that listens for 'Condition' messages
        related to the asset. The provided callback is invoked for each received message.

        Args:
            on_condition (AssetKafkaMessagesCallback): Callable that takes (msg_key: str, msg_value: dict) and handles condition messages.
            kafka_group_id (str): The Kafka consumer group ID to subscribe to.

        Returns:
            threading.Thread: The consumer thread that is now running.
        """
        return self.__subscribe("conditions", on_condition, kafka_group_id, expected_type="Condition")

    def stop_conditions_subscription(self) -> None:
        """
        Stops the Kafka consumer and gracefully shuts down the subscription.

        If a consumer instance exists, it is stopped and the associated consumer thread is joined.
        The consumer group is deleted from Kafka to clean up the subscription.
        """
        self.__stop_subscription("conditions")


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
