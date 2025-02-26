import json
from unittest import TestCase
from unittest.mock import patch, MagicMock
import pandas as pd
from openfactory.exceptions import OFAException
from openfactory.assets.asset import Asset


@patch("openfactory.assets.asset.KSQL")
@patch("openfactory.assets.asset.asyncio.run")
class TestAsset(TestCase):
    """
    Test class Asset
    """

    def test_asset_initialization_success(self, mock_async_run, MockKSQL):
        """ Test Asset initialization when asset exists """
        mock_ksql = MockKSQL.return_value
        test_df = pd.DataFrame({"TYPE": ["MockedType"]})
        mock_async_run.return_value = test_df

        asset = Asset("uuid-123")

        # Ensure correct attributes
        self.assertEqual(asset.asset_uuid, "uuid-123")
        self.assertEqual(asset.type, "MockedType")

        # Check if the correct query was executed
        expected_query = "SELECT TYPE FROM assets_type WHERE ASSET_UUID='uuid-123';"
        mock_ksql.query_to_dataframe.assert_called_once_with(expected_query)

    def test_asset_initialization_failure(self, mock_async_run, MockKSQL):
        """ Test Asset initialization when asset does not exist """
        mock_async_run.return_value = pd.DataFrame()  # Empty DataFrame (asset not found)

        with self.assertRaises(OFAException) as context:
            Asset("uuid-456")

        self.assertIn("Asset uuid-456 is not deployed in OpenFactory", str(context.exception))

    def test_attributes_success(self, mock_async_run, MockKSQL):
        """ Test attributes() returns correct attribute IDs """
        mock_ksql = MockKSQL.return_value

        asset_df = pd.DataFrame({"ASSET_UUID": "uuid-123",
                                 "TYPE": ["MockedType"]})
        attributes_df = pd.DataFrame({"ID": [101, 102, 103]})

        # Mock return values of asyncio.run
        mock_async_run.side_effect = [asset_df, attributes_df]

        asset = Asset("uuid-123")
        attributes = asset.attributes()

        self.assertEqual(attributes, [101, 102, 103])  # Expected list of IDs

        # Ensure correct query was exectued
        mock_ksql.query_to_dataframe.assert_any_call("SELECT ID FROM assets WHERE asset_uuid='uuid-123' AND TYPE != 'Method';")

    def test_attributes_empty(self, mock_async_run, MockKSQL):
        """ Test attributes() returns an empty list when no attributes exist """

        # Mock DataFrames
        asset_df = pd.DataFrame({"DEVICE_UUID": "uuid-123",
                                 "TYPE": ["MockedType"]})
        empty_attributes_df = pd.DataFrame(columns=["ID"])

        # Mock return values of asyncio.run
        mock_async_run.side_effect = [asset_df, empty_attributes_df]

        asset = Asset("uuid-456")
        attributes = asset.attributes()

        self.assertEqual(attributes, [])

    def test_samples(self, mock_async_run, MockKSQL):
        """ Test samples() """
        mock_ksql = MockKSQL.return_value

        asset_df = pd.DataFrame({"ASSET_UUID": "uuid-123",
                                 "TYPE": ["MockedType"]})
        samples_df = pd.DataFrame({"ID": ["id1"],
                                   "VALUE": ["val1"]})

        # Mock return values of asyncio.run
        mock_async_run.side_effect = [asset_df, samples_df]

        asset = Asset("uuid-123")
        samples = asset.samples()

        self.assertEqual(samples, {'id1': 'val1'})

        # Ensure correct query was exectued
        mock_ksql.query_to_dataframe.assert_any_call("SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='uuid-123' AND TYPE='Samples';")

    def test_events(self, mock_async_run, MockKSQL):
        """ Test events() """
        mock_ksql = MockKSQL.return_value

        asset_df = pd.DataFrame({"ASSET_UUID": "uuid-123",
                                 "TYPE": ["MockedType"]})
        events_df = pd.DataFrame({"ID": ["id2"],
                                  "VALUE": ["val2"]})

        # Mock return values of asyncio.run
        mock_async_run.side_effect = [asset_df, events_df]

        asset = Asset("uuid-123")
        events = asset.events()

        self.assertEqual(events, {'id2': 'val2'})

        # Ensure correct query was exectued
        mock_ksql.query_to_dataframe.assert_any_call("SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='uuid-123' AND TYPE='Events';")

    def test_conditions(self, mock_async_run, MockKSQL):
        """ Test conditions() """
        mock_ksql = MockKSQL.return_value

        asset_df = pd.DataFrame({"ASSET_UUID": "uuid-123",
                                 "TYPE": ["MockedType"]})
        cond_df = pd.DataFrame({
            "ID": ["id3"],
            "VALUE": ["val3"],
            "TAG": ["{urn:mtconnect.org:MTConnectStreams:2.2}Unavailable"]
        })

        # Mock return values of asyncio.run
        mock_async_run.side_effect = [asset_df, cond_df]

        asset = Asset("uuid-123")
        conditions = asset.conditions()

        expected_conditions = [{
            "ID": "id3",
            "VALUE": "val3",
            "TAG": "Unavailable"  # The namespace is removed
        }]
        self.assertEqual(conditions, expected_conditions)

        # Ensure correct query was exectued
        mock_ksql.query_to_dataframe.assert_any_call(
            "SELECT ID, VALUE, TAG, TYPE FROM assets WHERE ASSET_UUID='uuid-123' AND TYPE='Condition';"
        )

    def test_methods(self, mock_async_run, MockKSQL):
        """ Test methods() """
        mock_ksql = MockKSQL.return_value

        asset_df = pd.DataFrame({"ASSET_UUID": "uuid-123",
                                 "TYPE": ["MockedType"]})
        meth_df = pd.DataFrame({"ID": ["id4"],
                                "VALUE": ["val4"]})

        # Mock return values of asyncio.run
        mock_async_run.side_effect = [asset_df, meth_df]

        asset = Asset("uuid-123")
        methods = asset.methods()

        self.assertEqual(methods, {'id4': 'val4'})

        # Ensure correct query was exectued
        mock_ksql.query_to_dataframe.assert_any_call("SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='uuid-123' AND TYPE='Method';")

    @patch("openfactory.assets.asset.Producer")
    def test_method_execution(self, MockProducer, mock_async_run, MockKSQL):
        """ Test method() sends the correct Kafka message """
        mock_ksql = MockKSQL.return_value
        mock_producer = MockProducer.return_value
        asset_df = pd.DataFrame({"DEVICE_UUID": "uuid-123",
                                 "TYPE": ["MockedType"]})
        mock_async_run.side_effect = [asset_df]

        # Mock the Kafka topic resolution
        mock_ksql.get_kafka_topic.return_value = "test_topic"

        asset = Asset("uuid-123")

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
        mock_producer.produce.assert_called_once_with(
            topic="test_topic",
            key="uuid-123",
            value=json.dumps(expected_msg)
        )

        # Ensure flush() was called
        mock_producer.flush.assert_called_once()

    def test_getattr_samples(self, mock_async_run, MockKSQL):
        """ Test __getattr__ returns float for 'Samples' type """
        mock_ksql = MockKSQL.return_value

        asset_df = pd.DataFrame({"ASSET_UUID": "uuid-123",
                                 "TYPE": ["MockedType"]})
        query_df = pd.DataFrame({"ID": ["id1"],
                                 "VALUE": ["42.5"],
                                 "TYPE": ["Samples"]})

        mock_async_run.side_effect = [asset_df, query_df]

        asset = Asset("uuid-123")
        sample_value = asset.id1

        self.assertEqual(sample_value, 42.5)

        expected_query = "SELECT VALUE, TYPE FROM assets WHERE key='uuid-123|id1';"
        mock_ksql.query_to_dataframe.assert_any_call(expected_query)

    def test_getattr_string_value(self, mock_async_run, MockKSQL):
        """ Test __getattr__ returns raw VALUE for non-'Samples' and non-'Method' types """
        mock_ksql = MockKSQL.return_value

        asset_df = pd.DataFrame({"ASSET_UUID": "uuid-123",
                                 "TYPE": ["MockedType"]})
        query_df = pd.DataFrame({"ID": ["id2"],
                                 "VALUE": ["val2"],
                                 "TYPE": ["Events"]})

        mock_async_run.side_effect = [asset_df, query_df]

        asset = Asset("uuid-123")
        sample_value = asset.id2

        self.assertEqual(sample_value, "val2")

        expected_query = "SELECT VALUE, TYPE FROM assets WHERE key='uuid-123|id2';"
        mock_ksql.query_to_dataframe.assert_any_call(expected_query)

    @patch("openfactory.assets.asset.Asset.method")
    def test_getattr_method(self, mock_method, mock_async_run, MockKSQL):
        """ Test __getattr__ returns a callable for 'Method' type """
        mock_ksql = MockKSQL.return_value
        mock_method.return_value = "Mocked method called successfully"

        asset_df = pd.DataFrame({"ASSET_UUID": "uuid-123",
                                 "TYPE": ["MockedType"]})
        query_df = pd.DataFrame({"ID": ["a_method"],
                                 "VALUE": ["val4"],
                                 "TYPE": ["Method"]})

        mock_async_run.side_effect = [asset_df, query_df]

        asset = Asset("uuid-123")
        ret = asset.a_method('arg1', 'arg2')

        self.assertEqual(ret, "Mocked method called successfully")
        mock_method.assert_called_once_with("a_method", "arg1 arg2")

        expected_query = "SELECT VALUE, TYPE FROM assets WHERE key='uuid-123|a_method';"
        mock_ksql.query_to_dataframe.assert_any_call(expected_query)

    @patch("openfactory.assets.asset.Producer")
    def test_set_references(self, MockProducer, mock_async_run, MockKSQL):
        """ Test setting asset references """
        test_df = pd.DataFrame({"TYPE": ["MockedType"]})
        mock_async_run.return_value = test_df
        asset = Asset("asset-001")

        mock_producer = MockProducer.return_value
        mock_producer.produce = MagicMock()
        mock_producer.flush = MagicMock()

        # Call set_references
        asset.set_references("asset-002, asset-003")

        # Verify Kafka producer was called with the right arguments
        mock_producer.produce.assert_called_once()
        args, kwargs = mock_producer.produce.call_args
        self.assertEqual(kwargs['key'], "asset-001")
        self.assertEqual('{"ID": "references", "VALUE": "asset-002, asset-003", "TAG": "AssetsReferences", "TYPE": "OpenFactory"}', kwargs['value'])

        # Ensure flush was called
        mock_producer.flush.assert_called_once()

    def test_references_no_references(self, mock_async_run, MockKSQL):
        """ Test references when there are no linked assets """
        asset_df = pd.DataFrame({"ASSET_UUID": "uuid-123",
                                 "TYPE": ["MockedType"]})
        query_df = pd.DataFrame({})

        mock_async_run.side_effect = [asset_df, query_df]
        asset = Asset("asset-001")
        MockKSQL.query_to_dataframe.return_value = MagicMock(empty=True)

        # Expect an empty list
        self.assertEqual(asset.references, [])

    def test_references_with_data(self, mock_async_run, MockKSQL):
        """ Test references when assets are linked """

        # Mock the various assets/queries
        asset_df = pd.DataFrame({"ASSET_UUID": "uuid-123",
                                 "TYPE": ["MockedType"]})
        query_df = pd.DataFrame({"VALUE": ["asset-002, asset-003"]})
        asset2_df = pd.DataFrame({"ASSET_UUID": "asset-002",
                                  "TYPE": ["MockedType"]})
        asset3_df = pd.DataFrame({"ASSET_UUID": "asset-003",
                                  "TYPE": ["MockedType"]})
        mock_async_run.side_effect = [asset_df, query_df, asset2_df, asset3_df]
        asset = Asset("asset-001")

        # Expect references to return a list of Asset objects
        refs = asset.references
        self.assertEqual(len(refs), 2)
        self.assertIsInstance(refs[0], Asset)
        self.assertEqual(refs[0].asset_uuid, "asset-002")
        self.assertEqual(refs[1].asset_uuid, "asset-003")
