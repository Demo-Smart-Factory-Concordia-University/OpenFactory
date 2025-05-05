"""
Logging setup for OpenFactory.

This module provides a custom logging setup for the OpenFactory application.
"""

import logging


class PrefixFormatter(logging.Formatter):
    """ Custom formatter to add a prefix to log messages. """

    def __init__(self, prefix: str, fmt: str = None, datefmt: str = None):
        """
        Initialize the PrefixFormatter with a prefix.

        Args:
            prefix (str): The prefix to be added to log messages.
            fmt (str): The format string for the log message.
            datefmt (str): The format string for the date/time.
        """
        full_fmt = f"[{prefix}] {fmt or '%(levelname)s:%(name)s: %(message)s'}"
        super().__init__(full_fmt, datefmt)


def configure_prefixed_logger(name: str, level=logging.INFO, prefix="APP") -> logging.Logger:
    """
    Configure a logger with a specific name, level, and prefix.

    If the logger already exists, it will not be reconfigured.

    Args:
        name (str): The name of the logger.
        level (int): The logging level (default: logging.INFO).
        prefix (str): The prefix to be added to log messages (default: "APP").

    Returns:
        logging.Logger: The configured logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent adding multiple handlers on re-imports
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(PrefixFormatter(prefix))
        logger.addHandler(handler)

    # Prevent double logging to root
    logger.propagate = False

    return logger


def setup_third_party_loggers():
    """ Set up logging for third-party libraries with a specific prefix. """
    # Suppress or customize third-party libraries
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.WARNING)

    if not httpx_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(PrefixFormatter("HTTPX"))
        httpx_logger.addHandler(handler)
