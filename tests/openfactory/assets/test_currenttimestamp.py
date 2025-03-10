import unittest
from datetime import datetime, timezone
from openfactory.assets.asset_class import current_timestamp


class TestCurrentTimestamp(unittest.TestCase):

    def test_timestamp_format(self):
        """ Test that the timestamp has the correct ISO 8601 format with milliseconds and 'Z' timezone """
        timestamp = current_timestamp()

        # Example expected format: '2025-03-10T12:00:00.123Z'
        try:
            # Attempt to parse the timestamp — this checks the format
            parsed_time = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            self.fail(f"Timestamp '{timestamp}' is not in the expected format")

    def test_timestamp_is_recent(self):
        """ Test that the generated timestamp is close to the current time (within a few seconds) """
        now = datetime.now(timezone.utc)
        timestamp = current_timestamp()
        parsed_time = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)

        # Allow a small time difference (e.g., 1 seconds) due to execution time
        time_difference = abs((now - parsed_time).total_seconds())
        self.assertLess(time_difference, 1, f"Timestamp '{timestamp}' is not recent (difference: {time_difference}s)")
