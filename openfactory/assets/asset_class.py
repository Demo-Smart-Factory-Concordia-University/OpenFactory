""" OpenFactory Assets class. """

import json
import re
import threading
import uuid
import time
from confluent_kafka import KafkaError
from typing import Union, Literal, List, Dict, Protocol, Any, Optional
import openfactory.config as config
from openfactory.kafka import KafkaAssetConsumer, CaseInsensitiveDict, delete_consumer_group, KSQLDBClient
from openfactory.exceptions import OFAException
from openfactory.assets.utils import AssetAttribute
from openfactory.assets.kafka import AssetProducer, TypedKafkaConsumer


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

    def _get_reference_list(self, direction: str, as_assets: bool = False) -> List[Union[str, 'Asset']]:
        """
        Retrieves a list of asset references (UUIDs or Asset objects) in the given direction.

        Args:
            direction (str): Either 'above' or 'below', indicating reference direction.
            as_assets (bool): If True, returns Asset instances instead of UUID strings.

        Returns:
            List[Union[str, Asset]]: List of asset UUIDs or Asset objects.
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

    def references_above_uuid(self) -> List[str]:
        """
        Retrieves a list of asset UUIDs of assets above the current asset.

        Queries the `assets` table for the `VALUE` field associated with the key indicating
        the assets "above" the current one. If the `VALUE` field is empty or contains only
        whitespace, an empty list is returned. Otherwise, a list of asset UUIDs is returned.

        Returns:
            List[str]: A list of asset UUIDs (as strings) that are above the current asset.
        """
        return self._get_reference_list(direction="above", as_assets=False)

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
        return self._get_reference_list(direction="above", as_assets=True)

    def references_below_uuid(self) -> List[str]:
        """
        Retrieves a list of asset UUIDs below the current asset.

        Queries the `assets` table for the `VALUE` field associated with the key indicating
        the assets "below" the current one. If the `VALUE` field is empty or contains only
        whitespace, an empty list is returned. Otherwise, a list of asset UUIDs is returned.

        Returns:
            List[str]: A list of asset UUIDs (as strings) that are below the current asset.
        """
        return self._get_reference_list(direction="below", as_assets=False)

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
        return self._get_reference_list(direction="below", as_assets=True)

    def _add_reference(self, direction: str, new_reference: str) -> None:
        """
        Adds a reference to another asset in the specified direction.

        Args:
            direction (str): Either "above" or "below".
            new_reference (str): UUID of the asset to add as a reference.
        """
        key = f"{self.asset_uuid}|references_{direction}"
        query = f"SELECT VALUE FROM assets WHERE key='{key}';"
        df = self.ksql.query(query)

        if df.empty or df['VALUE'][0].strip() == "":
            references = new_reference
        else:
            references = f"{new_reference}, {df['VALUE'][0].strip()}"

        self.producer.send_asset_attribute(
            f"references_{direction}",
            AssetAttribute(
                value=references,
                tag="AssetsReferences",
                type="OpenFactory"
            )
        )

    def add_reference_above(self, above_asset_reference: str) -> None:
        """
        Adds a reference to an asset above the current asset.

        Queries the `assets` table to retrieve the current list of assets above the current asset.
        If there are existing references, the new reference is added to the list. Otherwise, the new reference
        becomes the only entry. The updated references are then sent to Kafka.

        Args:
            above_asset_reference (str): The asset UUID of the asset above the current one to be added.
        """
        self._add_reference(direction="above", new_reference=above_asset_reference)

    def add_reference_below(self, below_asset_reference: str) -> None:
        """
        Adds a reference to an asset below the current asset.

        Queries the `assets` table to retrieve the current list of assets below the current asset.
        If there are existing references, the new reference is added to the list. Otherwise, the new reference
        becomes the only entry. The updated references are then sent to Kafka.

        Args:
            below_asset_reference (str): The asset UUID of the asset below the current one to be added.
        """
        self._add_reference(direction="below", new_reference=below_asset_reference)

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
