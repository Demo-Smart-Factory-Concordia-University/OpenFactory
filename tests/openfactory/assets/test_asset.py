import json
from unittest import TestCase
from unittest.mock import patch, MagicMock
import pandas as pd
from openfactory.assets import Asset, AssetAttribute


@patch("openfactory.assets.asset_class.AssetProducer")
class TestAsset(TestCase):
    """
    Test class Asset
    """

    def test_asset_initialization_success(self, MockAssetProducer):
        """ Test Asset initialization when asset exists """
        asset = Asset("uuid-123", ksqlClient=MagicMock(), bootstrap_servers="mock_broker")

        # Ensure correct attributes
        self.assertEqual(asset.asset_uuid, "uuid-123")

    def test_type(self, MockAssetProducer):
        """ Test type when asset exists """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        ksqlMock.query.return_value = pd.DataFrame({"TYPE": ["MockedType"]})

        asset = Asset("uuid-123", ksqlClient=ksqlMock)

        self.assertEqual(asset.type, "MockedType")

        # Check if the correct query was executed
        expected_query = "SELECT TYPE FROM assets_type WHERE ASSET_UUID='uuid-123';"
        ksqlMock.query.assert_called_once_with(expected_query)

    def test_type_no_asset(self, MockAssetProducer):
        """ Test type when asset does not exists """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        ksqlMock.query.return_value = pd.DataFrame(columns=["ID"])

        asset = Asset("uuid-123", ksqlClient=ksqlMock)

        self.assertEqual(asset.type, "UNAVAILABLE")

        # Check if the correct query was executed
        expected_query = "SELECT TYPE FROM assets_type WHERE ASSET_UUID='uuid-123';"
        ksqlMock.query.assert_called_once_with(expected_query)

    def test_attributes_success(self, MockAssetProducer):
        """ Test attributes() returns correct attribute IDs """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        attributes_df = pd.DataFrame({"ID": [101, 102, 103]})
        ksqlMock.query.side_effect = [attributes_df]

        asset = Asset("uuid-123", ksqlClient=ksqlMock)
        attributes = asset.attributes()

        self.assertEqual(attributes, [101, 102, 103])  # Expected list of IDs

        # Ensure correct query was exectued
        expected_query = "SELECT ID FROM assets WHERE asset_uuid='uuid-123' AND TYPE != 'Method';"
        ksqlMock.query.assert_any_call(expected_query)

    def test_attributes_empty(self, MockAssetProducer):
        """ Test attributes() returns an empty list when no attributes exist """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        empty_attributes_df = pd.DataFrame(columns=["ID"])
        ksqlMock.query.side_effect = [empty_attributes_df]

        asset = Asset("uuid-456", ksqlClient=ksqlMock)
        attributes = asset.attributes()

        self.assertEqual(attributes, [])

    def test_samples(self, MockAssetProducer):
        """ Test samples() """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        samples_df = pd.DataFrame({"ID": ["id1"],
                                   "VALUE": ["val1"]})
        ksqlMock.query.side_effect = [samples_df]

        asset = Asset("uuid-123", ksqlClient=ksqlMock)
        samples = asset.samples()

        self.assertEqual(samples, {'id1': 'val1'})

        # Ensure correct query was exectued
        expected_query = "SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='uuid-123' AND TYPE='Samples';"
        ksqlMock.query.assert_any_call(expected_query)

    def test_events(self, MockAssetProducer):
        """ Test events() """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        events_df = pd.DataFrame({"ID": ["id2"],
                                  "VALUE": ["val2"]})
        ksqlMock.query.side_effect = [events_df]

        asset = Asset("uuid-123", ksqlClient=ksqlMock)
        events = asset.events()

        self.assertEqual(events, {'id2': 'val2'})

        # Ensure correct query was exectued
        expected_query = "SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='uuid-123' AND TYPE='Events';"
        ksqlMock.query.assert_any_call(expected_query)

    def test_conditions(self, MockAssetProducer):
        """ Test conditions() """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        cond_df = pd.DataFrame({
            "ID": ["id3"],
            "VALUE": ["val3"],
            "TAG": ["{urn:mtconnect.org:MTConnectStreams:2.2}Unavailable"]
        })
        ksqlMock.query.side_effect = [cond_df]

        asset = Asset("uuid-123", ksqlClient=ksqlMock)
        conditions = asset.conditions()

        expected_conditions = [{
            "ID": "id3",
            "VALUE": "val3",
            "TAG": "Unavailable"  # The namespace is removed
        }]
        self.assertEqual(conditions, expected_conditions)

        # Ensure correct query was exectued
        expected_query = "SELECT ID, VALUE, TAG, TYPE FROM assets WHERE ASSET_UUID='uuid-123' AND TYPE='Condition';"
        ksqlMock.query.assert_any_call(expected_query)

    def test_methods(self, MockAssetProducer):
        """ Test methods() """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        meth_df = pd.DataFrame({"ID": ["id4"],
                                "VALUE": ["val4"]})

        # Mock return values of asyncio.run
        ksqlMock.query.side_effect = [meth_df]

        asset = Asset("uuid-123", ksqlClient=ksqlMock)
        methods = asset.methods()

        self.assertEqual(methods, {'id4': 'val4'})

        # Ensure correct query was exectued
        expected_query = "SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='uuid-123' AND TYPE='Method';"
        ksqlMock.query.assert_any_call(expected_query)

    def test_method_execution(self, MockAssetProducer):
        """ Test method() sends the correct Kafka message """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        asset_df = pd.DataFrame({'ID': ["ID1"]})
        ksqlMock.query.side_effect = [asset_df]

        # Mock the Kafka topic resolution
        ksqlMock.get_kafka_topic.return_value = "test_topic"

        asset = Asset("uuid-123", ksqlClient=ksqlMock)
        asset.producer = MagicMock()
        ksqlMock.get_kafka_topic.reset_mock()

        # Call the method
        asset.method("start", "param1 param2")

        # Check Kafka topic resolution
        ksqlMock.get_kafka_topic.assert_called_once_with("CMDS_STREAM")

        # Expected message
        expected_msg = {
            "CMD": "start",
            "ARGS": "param1 param2"
        }

        # Ensure produce() was called with correct values
        asset.producer.produce.assert_called_once_with(
            topic="test_topic",
            key="uuid-123",
            value=json.dumps(expected_msg)
        )

        # Ensure flush() was called
        asset.producer.flush.assert_called_once()

    def test_getattr_samples(self, MockAssetProducer):
        """ Test __getattr__ returns float for 'Samples' type """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        query_df = pd.DataFrame({"ID": ["id1"],
                                 "VALUE": ["42.5"],
                                 "TYPE": ["Samples"],
                                 "TAG": ["MockedTag"],
                                 "TIMESTAMP": ["MockedTimeStamp"]})
        ksqlMock.query.side_effect = [query_df]

        asset = Asset("uuid-123", ksqlClient=ksqlMock)
        attribute = asset.id1

        self.assertEqual(attribute, AssetAttribute(value=42.5, type='Samples', tag='MockedTag', timestamp='MockedTimeStamp'))

        # Ensure correct query was exectued
        expected_query = "SELECT VALUE, TYPE, TAG, TIMESTAMP FROM assets WHERE key='uuid-123|id1';"
        ksqlMock.query.assert_any_call(expected_query)

    def test_getattr_string_value(self, MockAssetProducer):
        """ Test __getattr__ returns raw VALUE for non-'Samples' and non-'Method' types """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        query_df = pd.DataFrame({"ID": ["id2"],
                                 "VALUE": ["val2"],
                                 "TYPE": ["Events"],
                                 "TAG": ["MockedTag"],
                                 "TIMESTAMP": ["MockedTimeStamp"]})
        ksqlMock.query.side_effect = [query_df]

        asset = Asset("uuid-123", ksqlClient=ksqlMock)
        attribute = asset.id2

        self.assertEqual(attribute, AssetAttribute(value="val2", type='Events', tag='MockedTag', timestamp='MockedTimeStamp'))

        # Ensure correct query was exectued
        expected_query = "SELECT VALUE, TYPE, TAG, TIMESTAMP FROM assets WHERE key='uuid-123|id2';"
        ksqlMock.query.assert_any_call(expected_query)

    @patch("openfactory.assets.asset_class.Asset.method")
    def test_getattr_method(self, mock_method, MockAssetProducer):
        """ Test __getattr__ returns a callable for 'Method' type """
        mock_method.return_value = "Mocked method called successfully"

        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        query_df = pd.DataFrame({"ID": ["a_method"],
                                 "VALUE": ["val4"],
                                 "TYPE": ["Method"],
                                 "TAG": ["MockedTag"],
                                 "TIMESTAMP": ["MockedTimeStamp"]})

        ksqlMock.query.side_effect = [query_df]

        asset = Asset("uuid-123", ksqlClient=ksqlMock)
        ret = asset.a_method('arg1', 'arg2')

        self.assertEqual(ret, "Mocked method called successfully")
        mock_method.assert_called_once_with("a_method", "arg1 arg2")

        # Ensure correct query was exectued
        expected_query = "SELECT VALUE, TYPE, TAG, TIMESTAMP FROM assets WHERE key='uuid-123|a_method';"
        ksqlMock.query.assert_any_call(expected_query)

    def test_references_above_no_references(self, MockAssetProducer):
        """ Test references_above when there are no linked assets """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        ksqlMock.query.side_effect = [pd.DataFrame({})]
        asset = Asset("asset-001", ksqlClient=ksqlMock)

        # Expect an empty list
        self.assertEqual(asset.references_above, [])

    def test_references_above_with_data(self, MockAssetProducer):
        """ Test references_above when assets are linked """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        query_df = pd.DataFrame({"VALUE": ["asset-002, asset-003"]})
        ksqlMock.query.side_effect = [query_df]
        asset = Asset("uuid-123", ksqlClient=ksqlMock)

        # Expect references to return a list of Asset objects
        refs = asset.references_above
        self.assertEqual(len(refs), 2)
        self.assertIsInstance(refs[0], Asset)
        self.assertEqual(refs[0].asset_uuid, "asset-002")
        self.assertEqual(refs[1].asset_uuid, "asset-003")

    def test_references_below_no_references(self, MockAssetProducer):
        """ Test references_below when there are no linked assets """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        ksqlMock.query.side_effect = [pd.DataFrame({})]
        asset = Asset("asset-001", ksqlClient=ksqlMock)

        # Expect an empty list
        self.assertEqual(asset.references_below, [])

    def test_references_below_with_data(self, MockAssetProducer):
        """ Test references_below when assets are linked """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        query_df = pd.DataFrame({"VALUE": ["asset-002, asset-003"]})
        ksqlMock.query.side_effect = [query_df]
        asset = Asset("asset-001", ksqlClient=ksqlMock)

        # Expect references to return a list of Asset objects
        refs = asset.references_below
        self.assertEqual(len(refs), 2)
        self.assertIsInstance(refs[0], Asset)
        self.assertEqual(refs[0].asset_uuid, "asset-002")
        self.assertEqual(refs[1].asset_uuid, "asset-003")

    def test_add_reference_above_no_existing_reference(self, MockAssetProducer):
        """ Test add_reference_above when no existing references are present """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        query_df = pd.DataFrame(columns=['VALUE', 'ID'])
        ksqlMock.query.return_value = query_df
        asset = Asset("asset-001", ksqlClient=ksqlMock)
        asset.producer = MagicMock()

        # Call the method
        asset.add_reference_above("new-ref")

        # Ensure the correct query was executed
        expected_query = "SELECT VALUE FROM assets WHERE key='asset-001|references_above';"
        ksqlMock.query.assert_any_call(expected_query)

        # Capture the actual call arguments
        actual_call = asset.producer.send_asset_attribute.call_args
        _, actual_attribute = actual_call[0]  # Get the second positional argument (the AssetAttribute)

        # Check the non-timestamp fields
        assert actual_attribute.value == "new-ref"
        assert actual_attribute.type == "OpenFactory"
        assert actual_attribute.tag == "AssetsReferences"

    def test_add_reference_above_with_existing_reference(self, MockAssetProducer):
        """ Test add_reference_above when existing references are present """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        query_df = pd.DataFrame({'VALUE': ["existing-ref1, existing-ref2"],
                                 'ID': ["ID1"]})
        ksqlMock.query.return_value = query_df
        asset = Asset("asset-001", ksqlClient=ksqlMock)
        asset.producer = MagicMock()

        # Call the method
        asset.add_reference_above("new-ref")

        # Ensure the correct query was executed
        expected_query = "SELECT VALUE FROM assets WHERE key='asset-001|references_above';"
        ksqlMock.query.assert_any_call(expected_query)

        # Capture the actual call arguments
        actual_call = asset.producer.send_asset_attribute.call_args
        _, actual_attribute = actual_call[0]  # Get the second positional argument (the AssetAttribute)

        # Check the non-timestamp fields
        assert actual_attribute.value == "new-ref, existing-ref1, existing-ref2"
        assert actual_attribute.type == "OpenFactory"
        assert actual_attribute.tag == "AssetsReferences"

    def test_add_reference_below_no_existing_reference(self, MockAssetProducer):
        """ Test add_reference_below when no existing references are present """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        query_df = pd.DataFrame(columns=['VALUE', 'ID'])
        ksqlMock.query.return_value = query_df
        asset = Asset("asset-001", ksqlClient=ksqlMock)
        asset.producer = MagicMock()

        # Call the method
        asset.add_reference_below("new-ref")

        # Ensure the correct query was executed
        expected_query = "SELECT VALUE FROM assets WHERE key='asset-001|references_below';"
        ksqlMock.query.assert_any_call(expected_query)

        # Capture the actual call arguments
        actual_call = asset.producer.send_asset_attribute.call_args
        _, actual_attribute = actual_call[0]  # Get the second positional argument (the AssetAttribute)

        # Check the non-timestamp fields
        assert actual_attribute.value == "new-ref"
        assert actual_attribute.type == "OpenFactory"
        assert actual_attribute.tag == "AssetsReferences"

    def test_add_reference_below_with_existing_reference(self, MockAssetProducer):
        """ Test add_reference_below when existing references are present """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        query_df = pd.DataFrame({'VALUE': ["existing-ref1, existing-ref2"],
                                 'ID': ["ID1"]})
        ksqlMock.query.return_value = query_df
        asset = Asset("asset-001", ksqlClient=ksqlMock)
        asset.producer = MagicMock()

        # Call the method
        asset.add_reference_below("new-ref")

        # Ensure the correct query was executed
        expected_query = "SELECT VALUE FROM assets WHERE key='asset-001|references_below';"
        ksqlMock.query.assert_any_call(expected_query)

        # Capture the actual call arguments
        actual_call = asset.producer.send_asset_attribute.call_args
        _, actual_attribute = actual_call[0]  # Get the second positional argument (the AssetAttribute)

        # Check the non-timestamp fields
        assert actual_attribute.value == "new-ref, existing-ref1, existing-ref2"
        assert actual_attribute.type == "OpenFactory"
        assert actual_attribute.tag == "AssetsReferences"

    def test_references_above_uuid_empty_result(self, MockAssetProducer):
        """ Test references_above_uuid when the query returns an empty DataFrame """
        # Simulate an empty DataFrame returned by the query
        ksqlMock = MagicMock()
        ksqlMock.query.return_value = MagicMock(empty=True)
        asset = Asset("asset-001", ksqlClient=ksqlMock)

        result = asset.references_above_uuid()

        self.assertEqual(result, [])
        ksqlMock.query.assert_called_once_with(
            "SELECT VALUE, TYPE FROM assets WHERE key='asset-001|references_above';"
        )

    def test_references_above_uuid_no_value(self, MockAssetProducer):
        """ Test references_above_uuid when the VALUE field is empty """
        # Simulate a DataFrame with an empty VALUE field
        ksqlMock = MagicMock()
        ksqlMock.query.return_value = MagicMock(
            empty=False,
            __getitem__=lambda _, key: [""] if key == "VALUE" else None
        )
        asset = Asset("asset-001", ksqlClient=ksqlMock)

        result = asset.references_above_uuid()

        self.assertEqual(result, [])
        ksqlMock.query.assert_called_once_with(
            "SELECT VALUE, TYPE FROM assets WHERE key='asset-001|references_above';"
        )

    def test_references_above_uuid_with_values(self, MockAssetProducer):
        """ Test references_above_uuid when the VALUE field is not empty """
        # Simulate a DataFrame with a non-empty VALUE field
        ksqlMock = MagicMock()
        ksqlMock.query.return_value = MagicMock(
            empty=False,
            __getitem__=lambda _, key: ["uuid1, uuid2, uuid3"] if key == "VALUE" else None
        )
        asset = Asset("asset-001", ksqlClient=ksqlMock)

        result = asset.references_above_uuid()

        self.assertEqual(result, ["uuid1", "uuid2", "uuid3"])
        ksqlMock.query.assert_called_once_with(
            "SELECT VALUE, TYPE FROM assets WHERE key='asset-001|references_above';"
        )

    def test_references_below_uuid_empty_result(self, MockAssetProducer):
        """ Test references_below_uuid when the query returns an empty DataFrame """
        # Simulate an empty DataFrame returned by the query
        ksqlMock = MagicMock()
        ksqlMock.query.return_value = MagicMock(empty=True)
        asset = Asset("asset-001", ksqlClient=ksqlMock)

        result = asset.references_below_uuid()

        self.assertEqual(result, [])
        ksqlMock.query.assert_called_once_with(
            "SELECT VALUE, TYPE FROM assets WHERE key='asset-001|references_below';"
        )

    def test_references_below_uuid_no_value(self, MockAssetProducer):
        """ Test references_below_uuid when the VALUE field is empty """
        # Simulate a DataFrame with an empty VALUE field
        ksqlMock = MagicMock()
        ksqlMock.query.return_value = MagicMock(
            empty=False,
            __getitem__=lambda _, key: [""] if key == "VALUE" else None
        )
        asset = Asset("asset-001", ksqlClient=ksqlMock)

        result = asset.references_below_uuid()

        self.assertEqual(result, [])
        ksqlMock.query.assert_called_once_with(
            "SELECT VALUE, TYPE FROM assets WHERE key='asset-001|references_below';"
        )

    def test_references_below_uuid_with_values(self, MockAssetProducer):
        """ Test references_below_uuid when the VALUE field is not empty """
        # Simulate a DataFrame with a non-empty VALUE field
        ksqlMock = MagicMock()
        ksqlMock.query.return_value = MagicMock(
            empty=False,
            __getitem__=lambda _, key: ["uuid1, uuid2, uuid3"] if key == "VALUE" else None
        )
        asset = Asset("asset-001", ksqlClient=ksqlMock)

        result = asset.references_below_uuid()

        self.assertEqual(result, ["uuid1", "uuid2", "uuid3"])
        ksqlMock.query.assert_called_once_with(
            "SELECT VALUE, TYPE FROM assets WHERE key='asset-001|references_below';"
        )

    @patch('openfactory.assets.asset_class.KafkaAssetConsumer')
    @patch('openfactory.assets.asset_class.uuid.uuid4')
    @patch('openfactory.assets.asset_class.time.time')
    def test_wait_until_attribute_matches_initially(self, mock_time, mock_uuid, mock_kafka_consumer, MockAssetProducer):
        """ Test wait_until when the attribute matches initially """
        # Mock the Asset object
        mock_ksql = MagicMock()
        asset = Asset(asset_uuid="test_uuid", ksqlClient=mock_ksql)

        # Mock the attribute value to match
        mock_attribute = MagicMock()
        mock_attribute.value = "expected_value"
        asset.__getattr__ = MagicMock(return_value=mock_attribute)

        # Call the method
        result = asset.wait_until(attribute="test_attribute", value="expected_value")

        # Assert the result is True
        self.assertTrue(result)
        asset.__getattr__.assert_called_once_with("test_attribute")

    @patch('openfactory.assets.asset_class.KafkaAssetConsumer')
    @patch('openfactory.assets.asset_class.uuid.uuid4')
    @patch('openfactory.assets.asset_class.time.time')
    @patch('openfactory.assets.asset_class.delete_consumer_group')
    def test_wait_until_attribute_matches_after_polling(self, mock_delete_consumer_group, mock_time, mock_uuid, mock_kafka_consumer, MockAssetProducer):
        """ Test wait_until when the attribute matches after polling """
        # Mock the Asset object
        mock_ksql = MagicMock()
        asset = Asset(asset_uuid="test_uuid", ksqlClient=mock_ksql, bootstrap_servers="mock_broker")

        # Mock the attribute value to not match initially
        mock_attribute = MagicMock()
        mock_attribute.value = "initial_value"
        asset.__getattr__ = MagicMock(return_value=mock_attribute)

        # Mock Kafka consumer
        mock_consumer_instance = MagicMock()
        mock_kafka_consumer.return_value = mock_consumer_instance

        # Mock Kafka messages
        mock_message = MagicMock()
        mock_message.key.return_value = b"test_uuid"
        mock_message.value.return_value = b'{"id": "test_attribute", "type": "Events", "value": "expected_value"}'
        mock_message.error.return_value = False
        mock_consumer_instance.consumer.poll.side_effect = [None, mock_message]

        # Mock time for timeout
        mock_time.side_effect = [0, 1, 2]

        # Call the method
        mock_uuid.return_value = "mock"
        result = asset.wait_until(attribute="test_attribute", value="expected_value", timeout=10)

        # Assert the result is True
        self.assertTrue(result)
        mock_consumer_instance.consumer.close.assert_called_once()
        mock_delete_consumer_group.assert_called_once_with("test_uuid_mock", bootstrap_servers="mock_broker")

    @patch('openfactory.assets.asset_class.KafkaAssetConsumer')
    @patch('openfactory.assets.asset_class.uuid.uuid4')
    @patch('openfactory.assets.asset_class.time.time')
    @patch('openfactory.assets.asset_class.delete_consumer_group')
    def test_wait_until_attribute_matches_samples(self, mock_delete_consumer_group, mock_time, mock_uuid, mock_kafka_consumer, MockAssetProducer):
        """ Test wait_until when the attribute matches after polling for Samples attribute """
        # Mock the Asset object
        mock_ksql = MagicMock()
        asset = Asset(asset_uuid="test_uuid", ksqlClient=mock_ksql, bootstrap_servers="mock_broker")

        # Mock the attribute value to not match initially
        mock_attribute = MagicMock()
        mock_attribute.value = "initial_value"
        asset.__getattr__ = MagicMock(return_value=mock_attribute)

        # Mock Kafka consumer
        mock_consumer_instance = MagicMock()
        mock_kafka_consumer.return_value = mock_consumer_instance

        # Mock Kafka messages
        mock_message = MagicMock()
        mock_message.key.return_value = b"test_uuid"
        mock_message.value.return_value = b'{"id": "test_attribute", "type": "Samples", "value": "33"}'
        mock_message.error.return_value = False
        mock_consumer_instance.consumer.poll.side_effect = [None, mock_message]

        # Mock time for timeout
        mock_time.side_effect = [0, 1, 2]

        # Call the method
        mock_uuid.return_value = "mock"
        result = asset.wait_until(attribute="test_attribute", value=33, timeout=10)

        # Assert the result is True
        self.assertTrue(result)
        mock_consumer_instance.consumer.close.assert_called_once()
        mock_delete_consumer_group.assert_called_once_with("test_uuid_mock", bootstrap_servers="mock_broker")

    @patch('openfactory.assets.asset_class.KafkaAssetConsumer')
    @patch('openfactory.assets.asset_class.uuid.uuid4')
    @patch('openfactory.assets.asset_class.time.time')
    @patch('openfactory.assets.asset_class.delete_consumer_group')
    def test_wait_until_timeout(self, mock_delete_consumer_group, mock_time, mock_uuid, mock_kafka_consumer, MockAssetProducer):
        """ Test wait_until when the timeout is reached """
        # Mock the Asset object
        mock_ksql = MagicMock()
        asset = Asset(asset_uuid="test_uuid", ksqlClient=mock_ksql, bootstrap_servers="mock_broker")

        # Mock the attribute value to not match initially
        mock_attribute = MagicMock()
        mock_attribute.value = "initial_value"
        asset.__getattr__ = MagicMock(return_value=mock_attribute)

        # Mock Kafka consumer
        mock_consumer_instance = MagicMock()
        mock_kafka_consumer.return_value = mock_consumer_instance

        # Mock Kafka messages to return None (no matching messages)
        mock_consumer_instance.consumer.poll.return_value = None

        # Mock time for timeout
        mock_time.side_effect = [0, 1, 2, 31]

        # Call the method
        mock_uuid.return_value = "mock"
        result = asset.wait_until(attribute="test_attribute", value="expected_value", timeout=30)

        # Assert the result is False
        self.assertFalse(result)
        mock_consumer_instance.consumer.close.assert_called_once()
        mock_delete_consumer_group.assert_called_once_with("test_uuid_mock", bootstrap_servers="mock_broker")

    @patch('openfactory.assets.asset_class.KafkaAssetConsumer')
    @patch('openfactory.assets.asset_class.uuid.uuid4')
    @patch('openfactory.assets.asset_class.time.time')
    @patch('openfactory.assets.asset_class.delete_consumer_group')
    def test_wait_until_handles_invalid_message(self, mock_delete_consumer_group, mock_time, mock_uuid, mock_kafka_consumer, MockAssetProducer):
        """ Test wait_until when the message is invalid format """
        # Mock the Asset object
        mock_ksql = MagicMock()
        asset = Asset(asset_uuid="test_uuid", ksqlClient=mock_ksql, bootstrap_servers="mock_broker")

        # Mock the attribute value to not match initially
        mock_attribute = MagicMock()
        mock_attribute.value = "initial_value"
        asset.__getattr__ = MagicMock(return_value=mock_attribute)

        # Mock Kafka consumer
        mock_consumer_instance = MagicMock()
        mock_kafka_consumer.return_value = mock_consumer_instance

        # Mock Kafka messages with invalid data
        mock_message = MagicMock()
        mock_message.key.return_value = b"test_uuid"
        mock_message.value.return_value = b'invalid_json'
        mock_consumer_instance.consumer.poll.side_effect = [mock_message, None]

        # Mock time for timeout
        mock_time.side_effect = [0, 1, 31]

        # Call the method
        mock_uuid.return_value = "mock"
        result = asset.wait_until(attribute="test_attribute", value="expected_value", timeout=30)

        # Assert the result is False
        self.assertFalse(result)
        mock_consumer_instance.consumer.close.assert_called_once()
        mock_delete_consumer_group.assert_called_once_with("test_uuid_mock", bootstrap_servers="mock_broker")

    @patch('openfactory.assets.asset_class.time')
    def test_wait_until_ksqlDB_true(self, mock_time, MockAssetProducer):
        """ Test wait_until when use_ksqlDB is True """
        # Mock setup
        mock_time.time.side_effect = [0, 1, 2, 3, 4, 5]
        asset = Asset(asset_uuid="test_uuid", ksqlClient=MagicMock())
        asset.__getattr__ = MagicMock(side_effect=[MagicMock(value="initial"), MagicMock(value="target")])

        # Test when use_ksqlDB is True
        result = asset.wait_until(attribute="test_attribute", value="target", timeout=10, use_ksqlDB=True)
        self.assertTrue(result)

    @patch('openfactory.assets.asset_class.time')
    def test_wait_until_ksqlDB_timeout(self, mock_time, MockAssetProducer):
        """ Test wait_until when use_ksqlDB times out """
        # Mock setup
        mock_time.time.side_effect = [0, 1, 2, 3, 4, 5]
        asset = Asset(asset_uuid="test_uuid", ksqlClient=MagicMock())
        asset.__getattr__ = MagicMock(return_value=MagicMock(value="initial"))

        # Test timeout when use_ksqlDB is True
        result = asset.wait_until(attribute="test_attribute", value="target", timeout=3, use_ksqlDB=True)
        self.assertFalse(result)
