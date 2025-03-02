from unittest import TestCase
from unittest.mock import patch, MagicMock
from httpx import RequestError
import pandas as pd
from openfactory.exceptions import OFAException
from openfactory.assets.asset import Asset
from openfactory import OpenFactory


@patch("openfactory.openfactory.KSQL")
@patch("openfactory.openfactory.asyncio.run")
class TestOpenFactory(TestCase):

    def test_init_success(self, mock_async_run, MockKSQL):
        """ Test OpenFactory initialization when KSQL connection succeeds """
        mock_ksql = MockKSQL.return_value
        mock_ksql.info.return_value = {"status": "OK"}  # Simulate successful connection

        ofa = OpenFactory("http://fake-url")
        self.assertEqual(ofa.ksql, mock_ksql)

    def test_init_failure(self, mock_async_run, MockKSQL):
        """ Test OpenFactory initialization when KSQL connection fails """
        mock_ksql = MockKSQL.return_value
        mock_ksql.info.side_effect = RequestError("Connection failed")

        with self.assertRaises(OFAException) as context:
            OpenFactory("http://fake-url")

        self.assertIn("Could not connect", str(context.exception))

    def test_assets_empty(self, mock_async_run, MockKSQL):
        """ Test assets() when no assets exist """
        mock_async_run.return_value = pd.DataFrame()  # Simulate empty DataFrame

        ofa = OpenFactory("http://fake-url")
        assets = ofa.assets()

        self.assertEqual(assets, [])  # Expect an empty list

    def test_assets_with_data(self, mock_async_run, MockKSQL):
        """ Test assets() when assets exist """
        test_data = pd.DataFrame({"ASSET_UUID": ["uuid1", "uuid2"],
                                  "TYPE": ["type1", "type2"]})
        mock_async_run.return_value = test_data  # Simulate DataFrame with data

        ofa = OpenFactory("http://fake-url")
        assets = ofa.assets()

        self.assertEqual(len(assets), 2)
        self.assertIsInstance(assets[0], Asset)
        self.assertEqual(assets[0].asset_uuid, "uuid1")
        self.assertEqual(assets[1].asset_uuid, "uuid2")

    def test_assets_availability(self, mock_async_run, MockKSQL):
        """ Test assets_availability() """
        mock_ksql = MockKSQL.return_value
        mock_ksql.query_to_dataframe = MagicMock()
        test_df = pd.DataFrame({"ASSET_UUID": [1, 2], "available": ["AVAILABLE", "UNAVAILABLE"]})
        mock_async_run.return_value = test_df

        ofa = OpenFactory("http://fake-url")
        result = ofa.assets_availability()

        # Ensure the function returns the expected DataFrame
        pd.testing.assert_frame_equal(result, test_df)

        # Verify the correct query was executed
        mock_ksql.query_to_dataframe.assert_called_once_with("SELECT * FROM assets_avail;")

    def test_assets_docker_services(self, mock_async_run, MockKSQL):
        """ Test assets_docker_services() """
        mock_ksql = MockKSQL.return_value
        mock_ksql.query_to_dataframe = MagicMock()  # Mock the query method
        test_df = pd.DataFrame({"service_id": [1, 2], "status": ["running", "stopped"]})
        mock_async_run.return_value = test_df

        ofa = OpenFactory("http://fake-url")
        result = ofa.assets_docker_services()

        # Ensure the function returns the expected DataFrame
        pd.testing.assert_frame_equal(result, test_df)

        # Verify the correct query was executed
        mock_ksql.query_to_dataframe.assert_called_once_with("SELECT * FROM docker_services;")

    def test_devices_uuid(self, mock_async_run, MockKSQL):
        """ Test devices_uuid() """
        mock_ksql = MockKSQL.return_value
        mock_ksql.query_to_dataframe = MagicMock()
        test_df = pd.DataFrame({"ASSET_UUID": ["uuid1", "uuid2"]})
        mock_async_run.return_value = test_df

        ofa = OpenFactory("http://fake-url")
        result = ofa.devices_uuid()

        # Ensure the function returns the expected result
        self.assertEqual(result, ["uuid1", "uuid2"])

        # Verify the correct query was executed
        mock_ksql.query_to_dataframe.assert_called_once_with("SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'Device';")

    @patch("openfactory.openfactory.Asset")
    def test_devices(self, MockAsset, mock_async_run, MockKSQL):
        """ Test devices() """

        # Mock Asset instances
        mock_asset_instances = [MagicMock(), MagicMock()]
        MockAsset.side_effect = mock_asset_instances

        ksqldb_url = "http://fake-url"
        ofa = OpenFactory(ksqldb_url)
        ofa.devices_uuid = MagicMock()
        ofa.devices_uuid.return_value = ["asset-001", "asset-002"]

        result = ofa.devices()

        # Assert that Asset was called with the correct arguments
        MockAsset.assert_any_call(asset_uuid="asset-001", ksqldb_url=ksqldb_url)
        MockAsset.assert_any_call(asset_uuid="asset-002", ksqldb_url=ksqldb_url)

        # Assert that the return value matches the mock objects
        self.assertEqual(result, mock_asset_instances)

    def test_agents_uuid(self, mock_async_run, MockKSQL):
        """ Test agents_uuid() """
        mock_ksql = MockKSQL.return_value
        mock_ksql.query_to_dataframe = MagicMock()
        test_df = pd.DataFrame({"ASSET_UUID": ["uuid1", "uuid2"]})
        mock_async_run.return_value = test_df

        ofa = OpenFactory("http://fake-url")
        result = ofa.agents_uuid()

        # Ensure the function returns the expected result
        self.assertEqual(result, ["uuid1", "uuid2"])

        # Verify the correct query was executed
        mock_ksql.query_to_dataframe.assert_called_once_with("SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'MTConnectAgent';")

    @patch("openfactory.openfactory.Asset")
    def test_agents(self, MockAsset, mock_async_run, MockKSQL):
        """ Test agents() """

        # Mock Asset instances
        mock_asset_instances = [MagicMock(), MagicMock()]
        MockAsset.side_effect = mock_asset_instances

        ksqldb_url = "http://fake-url"
        ofa = OpenFactory(ksqldb_url)
        ofa.agents_uuid = MagicMock()
        ofa.agents_uuid.return_value = ["asset-001", "asset-002"]

        result = ofa.agents()

        # Assert that Asset was called with the correct arguments
        MockAsset.assert_any_call(asset_uuid="asset-001", ksqldb_url=ksqldb_url)
        MockAsset.assert_any_call(asset_uuid="asset-002", ksqldb_url=ksqldb_url)

        # Assert that the return value matches the mock objects
        self.assertEqual(result, mock_asset_instances)

    def test_producers_uuid(self, mock_async_run, MockKSQL):
        """ Test producers_uuid() """
        mock_ksql = MockKSQL.return_value
        mock_ksql.query_to_dataframe = MagicMock()
        test_df = pd.DataFrame({"ASSET_UUID": ["uuid1", "uuid2"]})
        mock_async_run.return_value = test_df

        ofa = OpenFactory("http://fake-url")
        result = ofa.producers_uuid()

        # Ensure the function returns the expected result
        self.assertEqual(result, ["uuid1", "uuid2"])

        # Verify the correct query was executed
        mock_ksql.query_to_dataframe.assert_called_once_with("SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'KafkaProducer';")

    @patch("openfactory.openfactory.Asset")
    def test_producers(self, MockAsset, mock_async_run, MockKSQL):
        """ Test producers() """

        # Mock Asset instances
        mock_asset_instances = [MagicMock(), MagicMock()]
        MockAsset.side_effect = mock_asset_instances

        ksqldb_url = "http://fake-url"
        ofa = OpenFactory(ksqldb_url)
        ofa.producers_uuid = MagicMock()
        ofa.producers_uuid.return_value = ["asset-001", "asset-002"]

        result = ofa.producers()

        # Assert that Asset was called with the correct arguments
        MockAsset.assert_any_call(asset_uuid="asset-001", ksqldb_url=ksqldb_url)
        MockAsset.assert_any_call(asset_uuid="asset-002", ksqldb_url=ksqldb_url)

        # Assert that the return value matches the mock objects
        self.assertEqual(result, mock_asset_instances)

    def test_supervisors_uuid(self, mock_async_run, MockKSQL):
        """ Test supervisors_uuid() """
        mock_ksql = MockKSQL.return_value
        mock_ksql.query_to_dataframe = MagicMock()
        test_df = pd.DataFrame({"ASSET_UUID": ["uuid1", "uuid2"]})
        mock_async_run.return_value = test_df

        ofa = OpenFactory("http://fake-url")
        result = ofa.supervisors_uuid()

        # Ensure the function returns the expected result
        self.assertEqual(result, ["uuid1", "uuid2"])

        # Verify the correct query was executed
        mock_ksql.query_to_dataframe.assert_called_once_with("SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'Supervisor';")

    @patch("openfactory.openfactory.Asset")
    def test_supervisors(self, MockAsset, mock_async_run, MockKSQL):
        """ Test supervisors() """

        # Mock Asset instances
        mock_asset_instances = [MagicMock(), MagicMock()]
        MockAsset.side_effect = mock_asset_instances

        ksqldb_url = "http://fake-url"
        ofa = OpenFactory(ksqldb_url)
        ofa.supervisors_uuid = MagicMock()
        ofa.supervisors_uuid.return_value = ["asset-001", "asset-002"]

        result = ofa.supervisors()

        # Assert that Asset was called with the correct arguments
        MockAsset.assert_any_call(asset_uuid="asset-001", ksqldb_url=ksqldb_url)
        MockAsset.assert_any_call(asset_uuid="asset-002", ksqldb_url=ksqldb_url)

        # Assert that the return value matches the mock objects
        self.assertEqual(result, mock_asset_instances)
