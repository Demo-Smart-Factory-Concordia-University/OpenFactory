import unittest
import json
from unittest.mock import MagicMock
from openfactory.assets.kafka import AssetProducer


class MockAssetAttribute:
    """
    Mock of AssetAttribute
    """
    def __init__(self):
        self.value = "123.45"
        self.type = "Samples"
        self.tag = "temperature"
        self.timestamp = "2025-06-24T10:00:00.123Z"


class TestAssetProducer(unittest.TestCase):
    """
    Test class AssetProducer
    """

    def test_init_sets_attributes_correctly(self):
        """ Test constructor """
        asset_uuid = "asset-xyz"
        expected_topic = "ASSETS_STREAM"

        mock_ksql = MagicMock()
        mock_ksql.get_kafka_topic.return_value = expected_topic

        producer = AssetProducer(asset_uuid, mock_ksql, bootstrap_servers="test-broker:9092")

        self.assertEqual(producer.asset_uuid, asset_uuid)
        self.assertEqual(producer.ksql, mock_ksql)
        self.assertEqual(producer.topic, expected_topic)

    def test_send_asset_attribute(self):
        """ Test send_asset_attribute """

        mock_ksql = MagicMock()
        mock_ksql.get_kafka_topic.return_value = "ASSETS_STREAM"
        asset_uuid = "asset-123"
        producer = AssetProducer(asset_uuid, mock_ksql)

        # Patch methods on the instance, not the class
        producer.produce = MagicMock()
        producer.flush = MagicMock()

        mock_attr = MockAssetAttribute()
        asset_id = "device-456"

        expected_message = {
            "ID": asset_id,
            "VALUE": mock_attr.value,
            "TAG": mock_attr.tag,
            "TYPE": mock_attr.type,
            "attributes": {
                "timestamp": mock_attr.timestamp
            }
        }

        producer.send_asset_attribute(asset_id, mock_attr)

        producer.produce.assert_called_once_with(
            topic="ASSETS_STREAM",
            key=asset_uuid,
            value=json.dumps(expected_message)
        )
        producer.flush.assert_called_once()
