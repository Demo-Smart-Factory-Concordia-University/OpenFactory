import unittest
from unittest.mock import Mock, MagicMock, patch
import json
import threading
import time
from confluent_kafka import KafkaError
from openfactory.kafka.commands_consumer import KafkaCommandsConsumer
from openfactory.kafka import CaseInsensitiveDict


class MockKafkaError:
    def code(self):
        return KafkaError.UNKNOWN


class MockKafkaMessage:
    """ Mock Kafka messages """

    def __init__(self, key=None, value=None, error=None):
        self._key = key
        self._value = value
        self._error = error

    def key(self):
        return self._key

    def value(self):
        # Ensure value is returned as bytes (so it can be decoded)
        if isinstance(self._value, str):
            return self._value.encode('utf-8')  # Convert to bytes if it's a string
        return self._value  # Otherwise, return as is (e.g., if it's already bytes)

    def error(self):
        return self._error


class TestKafkaCommandsConsumer(unittest.TestCase):
    """
    Test class KafkaCommandsConsumer
    """

    def setUp(self):
        # Mock the on_command callback function
        self.on_command_mock = Mock()

        # Mock the ksqlClient and its get_kafka_topic method
        self.ksqlClient_mock = Mock()
        self.ksqlClient_mock.get_kafka_topic.return_value = "test_cmds_topic"

        # Mock the Consumer class to prevent any actual Kafka connection
        self.mock_consumer = MagicMock()
        patch('openfactory.kafka.commands_consumer.Consumer', return_value=self.mock_consumer).start()

        # Create an instance of KafkaCommandsConsumer, Consumer is now mocked
        self.consumer = KafkaCommandsConsumer(
            consumer_group_id="test_group",
            asset_uuid="test_asset_uuid",
            on_command=self.on_command_mock,
            ksqlClient=self.ksqlClient_mock,
            bootstrap_servers="test_bootstrap"
        )

    def tearDown(self):
        # Stop patching after the test is complete
        patch.stopall()

    def test_consumer_stop(self):
        """ Test stop method """
        msg = MockKafkaMessage(
            key=b'test_asset_uuid',
            value=json.dumps({'key1': 'value1'}),
            error=None
        )
        self.mock_consumer.poll.return_value = msg
        consumer_thread = threading.Thread(target=self.consumer.consume)
        consumer_thread.start()

        # Allow some time for consume to start
        time.sleep(0.2)

        # Now stop the consumer
        self.consumer.stop()

        # Wait for the consumer thread to finish
        consumer_thread.join(timeout=2)

        # Ensure that the consumer's close method was called
        self.mock_consumer.close.assert_called_once()

        # Check if the thread actually terminated
        self.assertFalse(consumer_thread.is_alive(), "Consumer thread did not terminate")

    def test_consume_message(self):
        """ Test consumption of a message """
        def poll_side_effect():
            """ send a mocked message and then None forever """
            yield MockKafkaMessage(
                key=b'test_asset_uuid',
                value=json.dumps({'cmd': 'run', 'param': 'value'}),
                error=None
            )
            while True:
                yield None

        self.mock_consumer.poll.side_effect = poll_side_effect()

        # Start consumer in a thread
        consumer_thread = threading.Thread(target=self.consumer.consume)
        consumer_thread.start()

        # Wait for message processing
        timeout = time.time() + 0.5
        while not self.on_command_mock.called and time.time() < timeout:
            time.sleep(0.1)

        # Check if the on_command callback was called with the correct arguments
        self.on_command_mock.assert_called_once_with(
            'test_asset_uuid', CaseInsensitiveDict({'cmd': 'run', 'param': 'value'})
        )

        # Stop the consumer and join the thread
        self.consumer.stop()
        consumer_thread.join(timeout=2)
        self.assertFalse(consumer_thread.is_alive(), "Consumer thread did not terminate")

    def test_message_with_different_key(self):
        """ Test messages with wrong key get filtered out """
        def poll_side_effect():
            yield MockKafkaMessage(
                key=b'wrong_asset_uuid',
                value=json.dumps({'cmd': 'stop'}),
                error=None
            )
            while True:
                yield None

        self.mock_consumer.poll.side_effect = poll_side_effect()

        consumer_thread = threading.Thread(target=self.consumer.consume)
        consumer_thread.start()
        time.sleep(0.2)

        # Ensure on_command was not called since the key didn't match
        self.on_command_mock.assert_not_called()

        # Stop the consumer and clean up the thread
        self.consumer.stop()
        consumer_thread.join(timeout=2)
        self.assertFalse(consumer_thread.is_alive(), "Consumer thread did not terminate")

    def test_kafkaerror_in_consume_message(self):
        """ Test if KafkaError in message consumption closes consumer gracefully and logs error """
        error_msg = MockKafkaMessage(
            key=None,
            value=None,
            error=MockKafkaError()
        )
        self.mock_consumer.poll.side_effect = [error_msg]
        self.mock_consumer.subscribe.return_value = None

        with patch('openfactory.kafka.commands_consumer.kafka_logger') as mock_logger:
            # Run the consume method
            consumer_thread = threading.Thread(target=self.consumer.consume)
            consumer_thread.start()
            time.sleep(0.2)

            # Check that the error was logged
            error_logs = [call for call in mock_logger.error.call_args_list if "Error:" in str(call)]
            self.assertTrue(error_logs, "Expected Kafka error log not found")

            # Check that consumer gets closed after error
            self.mock_consumer.close.assert_called_once()

            # Ensure the consumer thread is closed gracefully
            self.consumer.stop()
            consumer_thread.join(timeout=2)
            self.assertFalse(consumer_thread.is_alive(), "Consumer thread did not terminate")

    def test_invalid_json_message(self):
        """ Test handling of invalid JSON message values """

        def poll_side_effect():
            yield MockKafkaMessage(
                key=b'test_asset_uuid',
                value=b'invalid_json_string',
                error=None
            )
            while True:
                yield None

        self.mock_consumer.poll.side_effect = poll_side_effect()

        with patch('openfactory.kafka.commands_consumer.kafka_logger') as mock_logger:
            consumer_thread = threading.Thread(target=self.consumer.consume)
            consumer_thread.start()
            time.sleep(0.2)

            # Ensure on_message was never called due to JSON decode failure
            self.on_command_mock.assert_not_called()

            # Check that the error was printed
            error_logs = [call for call in mock_logger.error.call_args_list if "Commands topic contained a none JSON value" in str(call)]
            self.assertTrue(error_logs, "Expected JSON decode error log not found")

            self.consumer.stop()
            consumer_thread.join(timeout=2)
            self.assertFalse(consumer_thread.is_alive(), "Consumer thread did not terminate")
        self.on_command_mock.assert_not_called()

    def test_filter_messages(self):
        """ Test for custom filter function """

        def custom_filter(msg_value):
            """ Filters out some specific messages """
            if 'SomeID' in msg_value:
                if msg_value['someid'] == 'We want this one':
                    return msg_value
            else:
                return None

        # Set the custom filter method
        self.consumer.filter_messages = custom_filter

        # Simulate a Kafka message
        def poll_side_effect():
            yield MockKafkaMessage(
                key=b'test_asset_uuid',
                value=json.dumps({'SomeID': 'Not of interest'}),
                error=None
            )
            yield MockKafkaMessage(
                key=b'test_asset_uuid',
                value=json.dumps({'SomeID': 'We want this one'}),
                error=None
            )
            while True:
                yield None

        self.mock_consumer.poll.side_effect = poll_side_effect()

        # Start consumer in thread
        consumer_thread = threading.Thread(target=self.consumer.consume)
        consumer_thread.start()

        # Wait for processing
        timeout = time.time() + 2
        while not self.on_command_mock.called and time.time() < timeout:
            time.sleep(0.1)

        # Verify that the filtered message was passed to on_command
        self.on_command_mock.assert_called_once_with(
            'test_asset_uuid', CaseInsensitiveDict({'SomeID': 'We want this one'})
        )

        # Stop consumer and cleanup
        self.consumer.stop()
        consumer_thread.join(timeout=2)
        self.assertFalse(consumer_thread.is_alive(), "Consumer thread did not terminate")
