import unittest
from unittest.mock import patch, MagicMock
from openfactory.utils import register_asset
from openfactory.assets import AssetAttribute


class TestRegisterAsset(unittest.TestCase):
    """
    Test register_asset
    """

    @patch("openfactory.utils.assets.AssetProducer")
    def test_register_asset_calls_send_asset_attribute_correctly(self, MockAssetProducer):
        """ Test register_asset logic """
        mock_producer_instance = MagicMock()
        MockAssetProducer.return_value = mock_producer_instance

        # Inputs
        asset_uuid = "1234-ABCD"
        asset_type = "Device"
        mock_ksql_client = MagicMock()
        bootstrap_servers = "kafka-broker:9092"
        docker_service = "robot-controller"

        # Call the function
        register_asset(asset_uuid, asset_type, mock_ksql_client, bootstrap_servers, docker_service)

        # Check that AssetProducer is instantiated correctly
        MockAssetProducer.assert_called_once_with(asset_uuid, mock_ksql_client, bootstrap_servers)

        # Check that send_asset_attribute is called four times with correct AssetAttribute values
        calls = mock_producer_instance.send_asset_attribute.call_args_list
        self.assertEqual(len(calls), 4)

        # Check contents of the first call
        asset_type_call = calls[0]
        self.assertEqual(asset_type_call[0][0], "AssetType")
        self.assertIsInstance(asset_type_call[0][1], AssetAttribute)
        self.assertEqual(asset_type_call[0][1].value, asset_type)
        self.assertEqual(asset_type_call[0][1].type, "OpenFactory")
        self.assertEqual(asset_type_call[0][1].tag, "AssetType")

        # Check contents of the second call
        docker_service_call = calls[1]
        self.assertEqual(docker_service_call[0][0], "DockerService")
        self.assertIsInstance(docker_service_call[0][1], AssetAttribute)
        self.assertEqual(docker_service_call[0][1].value, docker_service)
        self.assertEqual(docker_service_call[0][1].type, "OpenFactory")
        self.assertEqual(docker_service_call[0][1].tag, "DockerService")

        # Check contents of the third call
        docker_service_call = calls[2]
        self.assertEqual(docker_service_call[0][0], "references_below")
        self.assertIsInstance(docker_service_call[0][1], AssetAttribute)
        self.assertEqual(docker_service_call[0][1].value, "")
        self.assertEqual(docker_service_call[0][1].type, "OpenFactory")
        self.assertEqual(docker_service_call[0][1].tag, "AssetsReferences")

        # Check contents of the fourth call
        docker_service_call = calls[3]
        self.assertEqual(docker_service_call[0][0], "references_above")
        self.assertIsInstance(docker_service_call[0][1], AssetAttribute)
        self.assertEqual(docker_service_call[0][1].value, "")
        self.assertEqual(docker_service_call[0][1].type, "OpenFactory")
        self.assertEqual(docker_service_call[0][1].tag, "AssetsReferences")
