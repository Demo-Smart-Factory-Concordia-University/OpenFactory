import unittest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from openfactory.utils import register_asset
from openfactory.assets import AssetAttribute
from openfactory.utils.assets import now_iso_to_epoch_millis


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
        register_asset(asset_uuid, None, asset_type,
                       mock_ksql_client, bootstrap_servers, docker_service)

        # Check that AssetProducer is instantiated correctly
        MockAssetProducer.assert_called_once_with(asset_uuid, mock_ksql_client, bootstrap_servers)

        calls = mock_producer_instance.send_asset_attribute.call_args_list

        # We expect 4 fixed calls
        self.assertEqual(len(calls), 4)

        # Verify fixed attribute calls
        expected_fixed_attributes = [
            ("AssetType", asset_type, "AssetType"),
            ("DockerService", docker_service, "DockerService"),
            ("references_below", "", "AssetsReferences"),
            ("references_above", "", "AssetsReferences")
        ]

        for i, (key, value, tag) in enumerate(expected_fixed_attributes):
            call = calls[i]
            self.assertEqual(call[0][0], key)
            attr = call[0][1]
            self.assertIsInstance(attr, AssetAttribute)
            self.assertEqual(attr.value, value)
            self.assertEqual(attr.type, "OpenFactory")
            self.assertEqual(attr.tag, tag)

    @patch("openfactory.utils.assets.AssetProducer")
    def test_register_asset_sets_uns_mapping(self, MockAssetProducer):
        """ Test that UNS mapping is set correctly """
        mock_producer = MagicMock()
        MockAssetProducer.return_value = mock_producer

        # Inputs
        asset_uuid = "1234-ABCD"
        uns = {
            "levels": {
                "inc": "OpenFactory",
                "area": "Machining",
                "workcenter": "WC002",
                "asset": "cnc"
            },
            "uns_id": "OpenFactory/Machining/WC002/cnc"
        }
        asset_type = "Device"
        bootstrap_servers = "kafka-broker:9092"
        docker_service = "mocked_service"

        # Mock the KSQL client and its topic lookup
        mock_ksql_client = MagicMock()
        expected_topic = "mocked_asset_to_uns_map_topic"
        mock_ksql_client.get_kafka_topic.return_value = expected_topic

        # Patch now_iso_to_epoch_millis to return a fixed timestamp
        with patch("openfactory.utils.assets.now_iso_to_epoch_millis", return_value=1761338400000):
            register_asset(asset_uuid, uns, asset_type, mock_ksql_client, bootstrap_servers, docker_service)

        # Ensure get_kafka_topic was called with the correct table name
        mock_ksql_client.get_kafka_topic.assert_any_call("asset_to_uns_map_raw")

        # Assert correct call to produce()
        mock_producer.produce.assert_any_call(
            topic=expected_topic,
            key=asset_uuid.encode("utf-8"),
            value=json.dumps({
                "ASSET_UUID": asset_uuid,
                "UNS_ID": uns["uns_id"],
                "UNS_LEVELS": uns["levels"],
                "UPDATED_AT": 1761338400000
            })
        )

        # Assert flush was called
        mock_producer.flush.assert_called_once()


class TestNowIsoToEpochMillis(unittest.TestCase):
    """
    Test now_iso_to_epoch_millis
    """

    def test_returns_epoch_millis_close_to_now(self):
        """ Ensure the returned value is close to current UTC time in millis """
        before = int(datetime.now(timezone.utc).timestamp() * 1000)
        result = now_iso_to_epoch_millis()
        after = int(datetime.now(timezone.utc).timestamp() * 1000)

        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, before)
        self.assertLessEqual(result, after + 10)
