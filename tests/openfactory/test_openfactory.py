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
        test_data = pd.DataFrame({"DEVICE_UUID": ["uuid1", "uuid2"],
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
        test_df = pd.DataFrame({"DEVICE_UUID": [1, 2], "available": ["AVAILABLE", "UNAVAILABLE"]})
        mock_async_run.return_value = test_df

        ofa = OpenFactory("http://fake-url")
        result = ofa.assets_availability()

        # Ensure the function returns the expected DataFrame
        pd.testing.assert_frame_equal(result, test_df)

        # Verify the correct query was executed
        mock_ksql.query_to_dataframe.assert_called_once_with("SELECT * FROM devices_avail;")

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

    def test_devices(self, mock_async_run, MockKSQL):
        """ Test devices() """
        mock_ksql = MockKSQL.return_value
        mock_ksql.query_to_dataframe = MagicMock()
        test_df = pd.DataFrame({"DEVICE_UUID": ["uuid1", "uuid2"]})
        mock_async_run.return_value = test_df

        ofa = OpenFactory("http://fake-url")
        result = ofa.devices()

        # Ensure the function returns the expected result
        self.assertEqual(result, ["uuid1", "uuid2"])

        # Verify the correct query was executed
        mock_ksql.query_to_dataframe.assert_called_once_with("SELECT DEVICE_UUID FROM assets WHERE TYPE = 'Device';")

    def test_agents(self, mock_async_run, MockKSQL):
        """ Test agents() """
        mock_ksql = MockKSQL.return_value
        mock_ksql.query_to_dataframe = MagicMock()
        test_df = pd.DataFrame({"DEVICE_UUID": ["uuid1", "uuid2"]})
        mock_async_run.return_value = test_df

        ofa = OpenFactory("http://fake-url")
        result = ofa.agents()

        # Ensure the function returns the expected result
        self.assertEqual(result, ["uuid1", "uuid2"])

        # Verify the correct query was executed
        mock_ksql.query_to_dataframe.assert_called_once_with("SELECT DEVICE_UUID FROM assets WHERE TYPE = 'MTConnectAgent';")

    def test_producers(self, mock_async_run, MockKSQL):
        """ Test producers() """
        mock_ksql = MockKSQL.return_value
        mock_ksql.query_to_dataframe = MagicMock()
        test_df = pd.DataFrame({"DEVICE_UUID": ["uuid1", "uuid2"]})
        mock_async_run.return_value = test_df

        ofa = OpenFactory("http://fake-url")
        result = ofa.producers()

        # Ensure the function returns the expected result
        self.assertEqual(result, ["uuid1", "uuid2"])

        # Verify the correct query was executed
        mock_ksql.query_to_dataframe.assert_called_once_with("SELECT DEVICE_UUID FROM assets WHERE TYPE = 'KafkaProducer';")
