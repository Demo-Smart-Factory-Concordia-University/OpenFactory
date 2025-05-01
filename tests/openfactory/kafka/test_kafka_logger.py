import unittest
from unittest.mock import patch, MagicMock
import sys
import importlib
import logging


class TestKafkaLogger(unittest.TestCase):
    """
    Test kafka_logger setup
    """

    def tearDown(self):
        """
        Restore the kafka_logger module after test modifications to avoid affecting other tests.
        """
        if 'openfactory.kafka.kafka_logger' not in sys.modules:
            importlib.import_module('openfactory.kafka.kafka_logger')
        else:
            importlib.reload(sys.modules['openfactory.kafka.kafka_logger'])

    @patch('openfactory.setup_logging.configure_prefixed_logger')
    def test_kafka_logger_configuration(self, mock_configure_logger):
        """ Test that kafka_logger is configured with the correct prefix and log level """
        mock_logger = MagicMock()
        mock_configure_logger.return_value = mock_logger

        # Ensure fresh reload of the module (avoiding pre-imported state)
        with patch('openfactory.config.KAFKA_LOG_LEVEL', new='DEBUG'):
            sys.modules.pop('openfactory.kafka.kafka_logger', None)  # Remove the module if it was imported earlier
            import openfactory.kafka.kafka_logger as kafka_logger_module

        # Assert that the configure_prefixed_logger is called with correct arguments
        mock_configure_logger.assert_called_once_with(
            'openfactory.kafka',
            prefix='KAFKA',
            level='DEBUG'
        )

        # Verify that the `logger` property of the KafkaLogger instance is the mock_logger
        self.assertIs(kafka_logger_module.kafka_logger.logger, mock_logger)

    def test_set_level_and_get_level(self):
        """ Test dynamic log level adjustment via the level property """
        from openfactory.kafka.kafka_logger import kafka_logger
        # Set the level using the property
        kafka_logger.level = 'WARNING'

        # Assert internal numeric level was set
        self.assertEqual(kafka_logger.logger.level, logging.WARNING)

        # Assert property returns string version
        self.assertEqual(kafka_logger.level, 'WARNING')

    def test_delegation_via_getattr(self):
        """ Test that method delegation to the logger works correctly """
        from openfactory.kafka.kafka_logger import kafka_logger
        mock_logger = MagicMock()
        kafka_logger._logger = mock_logger

        # Call delegated method
        kafka_logger.debug("Test debug message")

        # Assert delegation worked
        mock_logger.debug.assert_called_once_with("Test debug message")
