import unittest
from unittest.mock import MagicMock, patch
from openfactory.kafka import KafkaAssetUNSConsumer
from openfactory.kafka import KafkaAssetConsumer


class TestKafkaAssetUNSConsumer(unittest.TestCase):
    """
    Test class KafkaAssetUNSConsumer
    """

    def setUp(self):
        self.consumer_group_id = "test-group"
        self.asset_uns_id = "asset-123"
        self.mock_on_message = MagicMock()
        self.mock_ksqlClient = MagicMock()
        self.bootstrap_servers = "localhost:9092"

    def test_derived_from_KafkaAssetConsumer(self):
        """ Test if derived from KafkaAssetConsumer """
        consumer = KafkaAssetUNSConsumer(
            self.consumer_group_id,
            self.asset_uns_id,
            self.mock_on_message,
            self.mock_ksqlClient,
            self.bootstrap_servers
        )

        self.assertIsInstance(consumer, KafkaAssetConsumer)

    def test_class_KSQL_ASSET_STREAM(self):
        """ Test if correct ksqlDB stream is defined """
        self.assertEqual(KafkaAssetUNSConsumer.KSQL_ASSET_STREAM, 'ASSETS_STREAM_UNS')

    @patch('openfactory.kafka.KafkaAssetConsumer.__init__', return_value=None)
    def test_super_init_called(self, mock_super_init):
        """ Test correct call of parent constructor """
        KafkaAssetUNSConsumer(
            self.consumer_group_id,
            self.asset_uns_id,
            self.mock_on_message,
            self.mock_ksqlClient,
            self.bootstrap_servers
        )
        mock_super_init.assert_called_once_with(
            self.consumer_group_id,
            self.asset_uns_id,
            self.mock_on_message,
            self.mock_ksqlClient,
            self.bootstrap_servers
        )
