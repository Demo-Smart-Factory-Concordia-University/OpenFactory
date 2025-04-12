import unittest
from unittest.mock import patch, MagicMock
from openfactory.utils import deregister_asset
from openfactory.assets import AssetAttribute


class TestDeregisterAsset(unittest.TestCase):
    """
    Test deregister_asset
    """

    @patch("openfactory.utils.assets.AssetProducer")
    def test_deregister_asset_calls_producer_correctly(self, MockAssetProducer):
        """ Test deregister_asset logic """

        mock_producer_instance = MagicMock()
        MockAssetProducer.return_value = mock_producer_instance

        # Inputs
        asset_uuid = "5678-EFGH"
        mock_ksql_client = MagicMock()
        mock_ksql_client.get_kafka_topic.side_effect = lambda table: f"topic_for_{table}"
        bootstrap_servers = "kafka-broker:9092"

        # Call the function
        deregister_asset(asset_uuid, mock_ksql_client, bootstrap_servers)

        # Check instantiation
        MockAssetProducer.assert_called_once_with(asset_uuid, mock_ksql_client, bootstrap_servers)

        # Check send_asset_attribute calls
        calls = mock_producer_instance.send_asset_attribute.call_args_list
        self.assertEqual(len(calls), 3)

        # Check first call: UNAVAILABLE message
        self.assertEqual(calls[0][0][0], "avail")
        self.assertIsInstance(calls[0][0][1], AssetAttribute)
        self.assertEqual(calls[0][0][1].value, "UNAVAILABLE")
        self.assertEqual(calls[0][0][1].type, "Events")
        self.assertEqual(calls[0][0][1].tag, "Availability")

        # Check reference removal messages
        expected_ids = ["references_below", "references_above"]
        for i, ref_id in enumerate(expected_ids, start=1):
            call = calls[i]
            self.assertEqual(call[0][0], ref_id)
            self.assertIsInstance(call[0][1], AssetAttribute)
            self.assertEqual(call[0][1].value, "")
            self.assertEqual(call[0][1].type, "OpenFactory")
            self.assertEqual(call[0][1].tag, "AssetsReferences")

        # Check produce tombstone messages
        expected_topics = ["assets_type", "docker_services"]
        for topic in expected_topics:
            mock_ksql_client.get_kafka_topic.assert_any_call(topic)
            mock_producer_instance.produce.assert_any_call(
                topic=f"topic_for_{topic}", key=asset_uuid, value=None
            )

        # Ensure flush was called
        mock_producer_instance.flush.assert_called_once()
