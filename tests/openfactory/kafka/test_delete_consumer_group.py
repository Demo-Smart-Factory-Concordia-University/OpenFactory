import unittest
from unittest.mock import patch, MagicMock
from openfactory.kafka import delete_consumer_group


class TestDeleteConsumerGroup(unittest.TestCase):
    """
    Tests for delete_consumer_group
    """

    @patch("openfactory.kafka.KafkaAdminClient")
    @patch("openfactory.kafka.kafka_logger")
    def test_delete_consumer_group_success(self, mock_logger, mock_admin_client_class):
        mock_admin_client = MagicMock()
        mock_admin_client_class.return_value = mock_admin_client

        delete_consumer_group("test-group", "mock_broker")

        mock_admin_client.delete_consumer_groups.assert_called_once_with(["test-group"])
        mock_logger.info.assert_called_with("Consumer group test-group deleted")

    @patch("openfactory.kafka.KafkaAdminClient")
    @patch("openfactory.kafka.kafka_logger")
    def test_delete_consumer_group_generic_exception(self, mock_logger, mock_admin_client_class):
        mock_admin_client = MagicMock()
        mock_admin_client.delete_consumer_groups.side_effect = Exception("Unexpected error")
        mock_admin_client_class.return_value = mock_admin_client

        delete_consumer_group("test-group")

        mock_logger.error.assert_called_with("Error deleting consumer group test-group: Unexpected error")
