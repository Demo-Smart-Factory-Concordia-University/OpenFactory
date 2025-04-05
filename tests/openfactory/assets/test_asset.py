import json
from unittest import TestCase
from unittest.mock import patch, MagicMock
import pandas as pd
from openfactory.assets import Asset, AssetAttribute


class TestAsset(TestCase):
    """
    Test class Asset
    """

    def test_asset_initialization_success(self):
        """ Test Asset initialization when asset exists """
        asset = Asset("uuid-123", ksqlClient=MagicMock())

        # Ensure correct attributes
        self.assertEqual(asset.asset_uuid, "uuid-123")

    def test_type(self):
        """ Test type when asset exists """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        ksqlMock.query.return_value = pd.DataFrame({"TYPE": ["MockedType"]})

        asset = Asset("uuid-123", ksqlClient=ksqlMock)

        self.assertEqual(asset.type, "MockedType")

        # Check if the correct query was executed
        expected_query = "SELECT TYPE FROM assets_type WHERE ASSET_UUID='uuid-123';"
        ksqlMock.query.assert_called_once_with(expected_query)

    def test_type_no_asset(self):
        """ Test type when asset does not exists """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        ksqlMock.query.return_value = pd.DataFrame(columns=["ID"])

        asset = Asset("uuid-123", ksqlClient=ksqlMock)

        self.assertEqual(asset.type, "UNAVAILABLE")

        # Check if the correct query was executed
        expected_query = "SELECT TYPE FROM assets_type WHERE ASSET_UUID='uuid-123';"
        ksqlMock.query.assert_called_once_with(expected_query)

    def test_attributes_success(self):
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

    def test_attributes_empty(self):
        """ Test attributes() returns an empty list when no attributes exist """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        empty_attributes_df = pd.DataFrame(columns=["ID"])
        ksqlMock.query.side_effect = [empty_attributes_df]

        asset = Asset("uuid-456", ksqlClient=ksqlMock)
        attributes = asset.attributes()

        self.assertEqual(attributes, [])

    def test_samples(self):
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

    def test_events(self):
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

    def test_conditions(self):
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

    def test_methods(self):
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

    def test_method_execution(self):
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

    def test_getattr_samples(self):
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

    def test_getattr_string_value(self):
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
    def test_getattr_method(self, mock_method):
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

    def test_references_above_no_references(self):
        """ Test references_above when there are no linked assets """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        ksqlMock.query.side_effect = [pd.DataFrame({})]
        asset = Asset("asset-001", ksqlClient=ksqlMock)

        # Expect an empty list
        self.assertEqual(asset.references_above, [])

    def test_references_above_with_data(self):
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

    def test_references_below_no_references(self):
        """ Test references_below when there are no linked assets """
        ksqlMock = MagicMock()
        ksqlMock.query_to_dataframe = MagicMock()
        ksqlMock.query.side_effect = [pd.DataFrame({})]
        asset = Asset("asset-001", ksqlClient=ksqlMock)

        # Expect an empty list
        self.assertEqual(asset.references_below, [])

    def test_references_below_with_data(self):
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

    def test_add_reference_above_no_existing_reference(self):
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

    def test_add_reference_above_with_existing_reference(self):
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

    def test_add_reference_below_no_existing_reference(self):
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

    def test_add_reference_below_with_existing_reference(self):
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
