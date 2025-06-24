import unittest
from unittest.mock import patch
from openfactory.kafka import KafkaAssetConsumer
from openfactory.assets.kafka import TypedKafkaConsumer


@patch.object(KafkaAssetConsumer, '__init__', return_value=None)
class TestTypedKafkaConsumer(unittest.TestCase):
    """
    Test class TypedKafkaConsumer
    """

    def test_init_sets_expected_type_and_calls_super(self, mock_super_init):
        """ Test constructor """
        expected_type = "Samples"
        mock_args = ("arg1",)
        mock_kwargs = {"some_kwarg": "value"}

        consumer = TypedKafkaConsumer(expected_type, *mock_args, **mock_kwargs)
        self.assertEqual(consumer.expected_type, expected_type)
        mock_super_init.assert_called_once_with(*mock_args, **mock_kwargs)

    def test_filter_messages_no_filtering(self, mock_super_init):
        """ Test filter_messages with expected_type=None """
        consumer = TypedKafkaConsumer(None)
        message = {"type": "Samples", "value": 42}
        result = consumer.filter_messages(message)
        self.assertEqual(result, message)

    def test_filter_messages_matching_type(self, mock_super_init):
        """ Test filter_messages with expected_type matching with Kafka message """
        consumer = TypedKafkaConsumer("Samples")
        message = {"type": "Samples", "value": 123}
        result = consumer.filter_messages(message)
        self.assertEqual(result, message)

    def test_filter_messages_non_matching_type(self, mock_super_init):
        """ Test filter_messages with expected_type not matching with Kafka message """
        consumer = TypedKafkaConsumer("Events")
        message = {"type": "Samples", "value": 123}
        result = consumer.filter_messages(message)
        self.assertIsNone(result)

    def test_filter_messages_missing_type_field(self, mock_super_init):
        """ Test filter_messages with missing type in Kafka message """
        consumer = TypedKafkaConsumer("Samples")
        message = {"value": 99}  # no 'type' key
        result = consumer.filter_messages(message)
        self.assertIsNone(result)
