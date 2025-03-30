import json
from unittest import TestCase
from unittest.mock import patch, MagicMock
import pandas as pd
from openfactory.assets import Asset, AssetAttribute


@patch("openfactory.assets.asset_class.KSQL")
@patch("openfactory.assets.asset_class.ksql_query_to_dataframe")
class TestAsset(TestCase):
    """
    Test class Asset
    """

    def test_asset_initialization_success(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test Asset initialization when asset exists """
        asset = Asset("uuid-123")

        # Ensure correct attributes
        self.assertEqual(asset.asset_uuid, "uuid-123")

    def test_type(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test type when asset exists """
        test_df = pd.DataFrame({"TYPE": ["MockedType"]})
        mock_ksql_query_to_dataframe.return_value = test_df

        asset = Asset("uuid-123", ksqldb_url='mock_ksqldb_url')

        self.assertEqual(asset.type, "MockedType")

        # Check if the correct query was executed
        expected_query = "SELECT TYPE FROM assets_type WHERE ASSET_UUID='uuid-123';"
        mock_ksql_query_to_dataframe.assert_called_once_with('mock_ksqldb_url', expected_query)

    def test_type_no_asset(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test type when asset does not exists """
        test_df = pd.DataFrame(columns=["ID"])
        mock_ksql_query_to_dataframe.return_value = test_df

        asset = Asset("uuid-123", ksqldb_url='mock_ksqldb_url')

        self.assertEqual(asset.type, "UNAVAILABLE")

        # Check if the correct query was executed
        expected_query = "SELECT TYPE FROM assets_type WHERE ASSET_UUID='uuid-123';"
        mock_ksql_query_to_dataframe.assert_called_once_with("mock_ksqldb_url", expected_query)

    def test_attributes_success(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test attributes() returns correct attribute IDs """
        attributes_df = pd.DataFrame({"ID": [101, 102, 103]})
        mock_ksql_query_to_dataframe.side_effect = [attributes_df]

        asset = Asset("uuid-123", ksqldb_url='mock_ksqldb_url')
        attributes = asset.attributes()

        self.assertEqual(attributes, [101, 102, 103])  # Expected list of IDs

        # Ensure correct query was exectued
        expected_query = "SELECT ID FROM assets WHERE asset_uuid='uuid-123' AND TYPE != 'Method';"
        mock_ksql_query_to_dataframe.assert_any_call("mock_ksqldb_url", expected_query)

    def test_attributes_empty(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test attributes() returns an empty list when no attributes exist """
        # Mock DataFrames
        empty_attributes_df = pd.DataFrame(columns=["ID"])

        # Mock return values of asyncio.run
        mock_ksql_query_to_dataframe.side_effect = [empty_attributes_df]

        asset = Asset("uuid-456")
        attributes = asset.attributes()

        self.assertEqual(attributes, [])

    def test_samples(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test samples() """
        samples_df = pd.DataFrame({"ID": ["id1"],
                                   "VALUE": ["val1"]})
        mock_ksql_query_to_dataframe.side_effect = [samples_df]

        asset = Asset("uuid-123", ksqldb_url='mock_ksqldb_url')
        samples = asset.samples()

        self.assertEqual(samples, {'id1': 'val1'})

        # Ensure correct query was exectued
        expected_query = "SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='uuid-123' AND TYPE='Samples';"
        mock_ksql_query_to_dataframe.assert_any_call('mock_ksqldb_url', expected_query)

    def test_events(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test events() """
        events_df = pd.DataFrame({"ID": ["id2"],
                                  "VALUE": ["val2"]})
        mock_ksql_query_to_dataframe.side_effect = [events_df]

        asset = Asset("uuid-123", ksqldb_url='mock_ksqldb_url')
        events = asset.events()

        self.assertEqual(events, {'id2': 'val2'})

        # Ensure correct query was exectued
        expected_query = "SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='uuid-123' AND TYPE='Events';"
        mock_ksql_query_to_dataframe.assert_any_call('mock_ksqldb_url', expected_query)

    def test_conditions(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test conditions() """
        cond_df = pd.DataFrame({
            "ID": ["id3"],
            "VALUE": ["val3"],
            "TAG": ["{urn:mtconnect.org:MTConnectStreams:2.2}Unavailable"]
        })

        # Mock return values of asyncio.run
        mock_ksql_query_to_dataframe.side_effect = [cond_df]

        asset = Asset("uuid-123", ksqldb_url='mock_ksqldb_url')
        conditions = asset.conditions()

        expected_conditions = [{
            "ID": "id3",
            "VALUE": "val3",
            "TAG": "Unavailable"  # The namespace is removed
        }]
        self.assertEqual(conditions, expected_conditions)

        # Ensure correct query was exectued
        expected_query = "SELECT ID, VALUE, TAG, TYPE FROM assets WHERE ASSET_UUID='uuid-123' AND TYPE='Condition';"
        mock_ksql_query_to_dataframe.assert_any_call('mock_ksqldb_url', expected_query)

    def test_methods(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test methods() """
        meth_df = pd.DataFrame({"ID": ["id4"],
                                "VALUE": ["val4"]})

        # Mock return values of asyncio.run
        mock_ksql_query_to_dataframe.side_effect = [meth_df]

        asset = Asset("uuid-123", ksqldb_url='mock_ksqldb_url')
        methods = asset.methods()

        self.assertEqual(methods, {'id4': 'val4'})

        # Ensure correct query was exectued
        expected_query = "SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='uuid-123' AND TYPE='Method';"
        mock_ksql_query_to_dataframe.assert_any_call('mock_ksqldb_url', expected_query)

    def test_method_execution(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test method() sends the correct Kafka message """
        mock_ksql = MockKSQL.return_value
        asset_df = pd.DataFrame({'ID': ["ID1"]})
        mock_ksql_query_to_dataframe.side_effect = [asset_df]

        # Mock the Kafka topic resolution
        mock_ksql.get_kafka_topic.return_value = "test_topic"

        asset = Asset("uuid-123")
        asset.producer = MagicMock()
        mock_ksql.get_kafka_topic.reset_mock()

        # Call the method
        asset.method("start", "param1 param2")

        # Check Kafka topic resolution
        mock_ksql.get_kafka_topic.assert_called_once_with("CMDS_STREAM")

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

    def test_getattr_samples(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test __getattr__ returns float for 'Samples' type """
        query_df = pd.DataFrame({"ID": ["id1"],
                                 "VALUE": ["42.5"],
                                 "TYPE": ["Samples"],
                                 "TAG": ["MockedTag"],
                                 "TIMESTAMP": ["MockedTimeStamp"]})

        mock_ksql_query_to_dataframe.side_effect = [query_df]

        asset = Asset("uuid-123", ksqldb_url='mock_ksqldb_url')
        attribute = asset.id1

        self.assertEqual(attribute, AssetAttribute(value=42.5, type='Samples', tag='MockedTag', timestamp='MockedTimeStamp'))

        # Ensure correct query was exectued
        expected_query = "SELECT VALUE, TYPE, TAG, TIMESTAMP FROM assets WHERE key='uuid-123|id1';"
        mock_ksql_query_to_dataframe.assert_any_call('mock_ksqldb_url', expected_query)

    def test_getattr_string_value(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test __getattr__ returns raw VALUE for non-'Samples' and non-'Method' types """
        query_df = pd.DataFrame({"ID": ["id2"],
                                 "VALUE": ["val2"],
                                 "TYPE": ["Events"],
                                 "TAG": ["MockedTag"],
                                 "TIMESTAMP": ["MockedTimeStamp"]})
        mock_ksql_query_to_dataframe.side_effect = [query_df]

        asset = Asset("uuid-123", ksqldb_url='mock_ksqldb_url')
        attribute = asset.id2

        self.assertEqual(attribute, AssetAttribute(value="val2", type='Events', tag='MockedTag', timestamp='MockedTimeStamp'))

        # Ensure correct query was exectued
        expected_query = "SELECT VALUE, TYPE, TAG, TIMESTAMP FROM assets WHERE key='uuid-123|id2';"
        mock_ksql_query_to_dataframe.assert_any_call('mock_ksqldb_url', expected_query)

    @patch("openfactory.assets.asset_class.Asset.method")
    def test_getattr_method(self, mock_method, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test __getattr__ returns a callable for 'Method' type """
        mock_method.return_value = "Mocked method called successfully"

        query_df = pd.DataFrame({"ID": ["a_method"],
                                 "VALUE": ["val4"],
                                 "TYPE": ["Method"],
                                 "TAG": ["MockedTag"],
                                 "TIMESTAMP": ["MockedTimeStamp"]})

        mock_ksql_query_to_dataframe.side_effect = [query_df]

        asset = Asset("uuid-123", ksqldb_url='mock_ksqldb_url')
        ret = asset.a_method('arg1', 'arg2')

        self.assertEqual(ret, "Mocked method called successfully")
        mock_method.assert_called_once_with("a_method", "arg1 arg2")

        # Ensure correct query was exectued
        expected_query = "SELECT VALUE, TYPE, TAG, TIMESTAMP FROM assets WHERE key='uuid-123|a_method';"
        mock_ksql_query_to_dataframe.assert_any_call('mock_ksqldb_url', expected_query)

    def test_references_above_no_references(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test references_above when there are no linked assets """
        query_df = pd.DataFrame({})
        mock_ksql_query_to_dataframe.side_effect = [query_df]
        asset = Asset("asset-001")

        # Expect an empty list
        self.assertEqual(asset.references_above, [])

    def test_references_above_with_data(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test references_above when assets are linked """
        query_df = pd.DataFrame({"VALUE": ["asset-002, asset-003"]})
        mock_ksql_query_to_dataframe.side_effect = [query_df]
        asset = Asset("uuid-123")

        # Expect references to return a list of Asset objects
        refs = asset.references_above
        self.assertEqual(len(refs), 2)
        self.assertIsInstance(refs[0], Asset)
        self.assertEqual(refs[0].asset_uuid, "asset-002")
        self.assertEqual(refs[1].asset_uuid, "asset-003")

    def test_references_below_no_references(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test references_below when there are no linked assets """
        query_df = pd.DataFrame({})
        mock_ksql_query_to_dataframe.side_effect = [query_df]
        asset = Asset("asset-001")

        # Expect an empty list
        self.assertEqual(asset.references_below, [])

    def test_references_below_with_data(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test references_below when assets are linked """
        query_df = pd.DataFrame({"VALUE": ["asset-002, asset-003"]})
        mock_ksql_query_to_dataframe.side_effect = [query_df]
        asset = Asset("asset-001")

        # Expect references to return a list of Asset objects
        refs = asset.references_below
        self.assertEqual(len(refs), 2)
        self.assertIsInstance(refs[0], Asset)
        self.assertEqual(refs[0].asset_uuid, "asset-002")
        self.assertEqual(refs[1].asset_uuid, "asset-003")

    def test_add_reference_above_no_existing_reference(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test add_reference_above when no existing references are present """

        # Mock Asset instance
        query_df = pd.DataFrame(columns=['VALUE', 'ID'])
        mock_ksql_query_to_dataframe.return_value = query_df
        asset = Asset("asset-001", ksqldb_url='mock_ksqldb_url')
        asset.producer = MagicMock()

        # Call the method
        asset.add_reference_above("new-ref")

        # Ensure the correct query was executed
        expected_query = "SELECT VALUE FROM assets WHERE key='asset-001|references_above';"
        mock_ksql_query_to_dataframe.assert_any_call('mock_ksqldb_url', expected_query)

        # Capture the actual call arguments
        actual_call = asset.producer.send_asset_attribute.call_args
        _, actual_attribute = actual_call[0]  # Get the second positional argument (the AssetAttribute)

        # Check the non-timestamp fields
        assert actual_attribute.value == "new-ref"
        assert actual_attribute.type == "OpenFactory"
        assert actual_attribute.tag == "AssetsReferences"

    def test_add_reference_above_with_existing_reference(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test add_reference_above when existing references are present """

        # Mock Asset instance
        query_df = pd.DataFrame({'VALUE': ["existing-ref1, existing-ref2"],
                                 'ID': ["ID1"]})
        mock_ksql_query_to_dataframe.return_value = query_df
        asset = Asset("asset-001", ksqldb_url='mock_ksqldb_url')
        asset.producer = MagicMock()

        # Call the method
        asset.add_reference_above("new-ref")

        # Ensure the correct query was executed
        expected_query = "SELECT VALUE FROM assets WHERE key='asset-001|references_above';"
        mock_ksql_query_to_dataframe.assert_any_call('mock_ksqldb_url', expected_query)

        # Capture the actual call arguments
        actual_call = asset.producer.send_asset_attribute.call_args
        _, actual_attribute = actual_call[0]  # Get the second positional argument (the AssetAttribute)

        # Check the non-timestamp fields
        assert actual_attribute.value == "new-ref, existing-ref1, existing-ref2"
        assert actual_attribute.type == "OpenFactory"
        assert actual_attribute.tag == "AssetsReferences"

    def test_add_reference_below_no_existing_reference(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test add_reference_below when no existing references are present """

        # Mock Asset instance
        query_df = pd.DataFrame(columns=['VALUE', 'ID'])
        mock_ksql_query_to_dataframe.return_value = query_df
        asset = Asset("asset-001", ksqldb_url='mock_ksqldb_url')
        asset.producer = MagicMock()

        # Call the method
        asset.add_reference_below("new-ref")

        # Ensure the correct query was executed
        expected_query = "SELECT VALUE FROM assets WHERE key='asset-001|references_below';"
        mock_ksql_query_to_dataframe.assert_any_call('mock_ksqldb_url', expected_query)

        # Capture the actual call arguments
        actual_call = asset.producer.send_asset_attribute.call_args
        _, actual_attribute = actual_call[0]  # Get the second positional argument (the AssetAttribute)

        # Check the non-timestamp fields
        assert actual_attribute.value == "new-ref"
        assert actual_attribute.type == "OpenFactory"
        assert actual_attribute.tag == "AssetsReferences"

    def test_add_reference_below_with_existing_reference(self, mock_ksql_query_to_dataframe, MockKSQL):
        """ Test add_reference_below when existing references are present """

        # Mock Asset instance
        query_df = pd.DataFrame({'VALUE': ["existing-ref1, existing-ref2"],
                                 'ID': ["ID1"]})
        mock_ksql_query_to_dataframe.return_value = query_df
        asset = Asset("asset-001", ksqldb_url='mock_ksqldb_url')
        asset.producer = MagicMock()

        # Call the method
        asset.add_reference_below("new-ref")

        # Ensure the correct query was executed
        expected_query = "SELECT VALUE FROM assets WHERE key='asset-001|references_below';"
        mock_ksql_query_to_dataframe.assert_any_call('mock_ksqldb_url', expected_query)

        # Capture the actual call arguments
        actual_call = asset.producer.send_asset_attribute.call_args
        _, actual_attribute = actual_call[0]  # Get the second positional argument (the AssetAttribute)

        # Check the non-timestamp fields
        assert actual_attribute.value == "new-ref, existing-ref1, existing-ref2"
        assert actual_attribute.type == "OpenFactory"
        assert actual_attribute.tag == "AssetsReferences"
