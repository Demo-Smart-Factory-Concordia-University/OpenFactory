""" OpenFactory Assets helper functions. """

from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Union, Literal


def current_timestamp() -> str:
    """
    Returns the current timestamp in OpenFactory format.

    The format is ISO 8601 with milliseconds precision and a 'Z' to indicate UTC time,
    e.g., '2025-05-04T12:34:56.789Z'.

    Returns:
        str: The current UTC timestamp formatted in OpenFactory style.
    """
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


@dataclass
class AssetAttribute:
    """
    Represents a single attribute of an asset, including its value, type, tag, and timestamp.

    Attributes:
        value (Union[str, float]): The actual value of the attribute. Can be a string or float.
        type (Literal['Samples', 'Condition', 'Events', 'Method', 'OpenFactory', 'UNAVAILABLE']):
            The category/type of the attribute, must be one of the allowed literal strings.
        tag (str): The tag or identifier associated with this attribute.
        timestamp (str): Timestamp when the attribute was recorded, in OpenFactory format.
                         Defaults to the current timestamp if not provided.
    """

    value: Union[str, float]
    type: Literal['Samples', 'Condition', 'Events', 'Method', 'OpenFactory', 'UNAVAILABLE']
    tag: str
    timestamp: str = field(default_factory=current_timestamp)

    def __post_init__(self) -> None:
        """
        Validates the type of the attribute after initialization.

        Raises:
            ValueError: If the type is not one of the allowed literal strings.
        """
        ALLOWED_TYPES = {'Samples', 'Condition', 'Events', 'Method', 'OpenFactory', 'UNAVAILABLE'}
        if self.type not in ALLOWED_TYPES:
            raise ValueError(f"Invalid type '{self.type}'. Allowed values are: {', '.join(ALLOWED_TYPES)}")
