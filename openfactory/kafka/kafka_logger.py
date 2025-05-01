""" OpenFactory Kafka logger. """

import logging
from openfactory.setup_logging import configure_prefixed_logger
import openfactory.config as config


class KafkaLogger:
    """ Kafka Logger for centralized logging configuration. """

    def __init__(self) -> None:
        """ Initialize the KafkaLogger with default configuration. """
        self._logger = configure_prefixed_logger(
            'openfactory.kafka',
            prefix='KAFKA',
            level=config.KAFKA_LOG_LEVEL
        )

    @property
    def logger(self) -> logging.Logger:
        """
        Access the configured logger instance.

        Returns:
            logging.Logger: The logger instance.
        """
        return self._logger

    @property
    def level(self) -> str:
        """
        Get the current log level as a string.

        Returns:
            str: The log level name (e.g., 'WARNING', 'DEBUG').
        """
        return logging.getLevelName(self.logger.level)

    @level.setter
    def level(self, level: str) -> None:
        """
        Set the logger's log level.

        Args:
            level (str): The desired log level name.
        """
        self.logger.setLevel(level)

    def __getattr__(self, item: str):
        """
        Delegate attribute access to the internal logger.

        Allows calls like:
        ```python
        from openfactory.kafka.kafka_logger import kafka_logger
        kafka_logger.debug("...")
        ```

        Args:
            item (str): The attribute name.

        Returns:
            Any: The attribute from the internal logger.
        """
        return getattr(self.logger, item)


# Singleton instance
kafka_logger = KafkaLogger()
