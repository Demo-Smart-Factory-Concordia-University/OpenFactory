import unittest
from datetime import datetime, timezone
from openfactory.assets.asset_class import AssetAttribute


class TestAssetAttribute(unittest.TestCase):

    def test_create_with_defaults(self):
        """ Test creating an AssetAttribute with default timestamp """
        attr = AssetAttribute(value=123, type="Events", tag="MockTag")

        self.assertEqual(attr.value, 123)
        self.assertEqual(attr.type, "Events")
        self.assertEqual(attr.tag, "MockTag")

        # Check that the timestamp was set and matches the expected format
        try:
            datetime.strptime(attr.timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            self.fail(f"Timestamp '{attr.timestamp}' is not in the expected format")

    def test_valid_types(self):
        """ Test AssetAttribute instantiation with valid type values """
        valid_types = ['Samples', 'Condition', 'Events', 'Method', 'OpenFactory']
        for t in valid_types:
            with self.subTest(type=t):
                obj = AssetAttribute(value=42.0, type=t, tag="MockTag")
                self.assertEqual(obj.type, t)

    def test_invalid_type(self):
        """ Test that an invalid type raises ValueError """
        with self.assertRaises(ValueError) as context:
            AssetAttribute(value=42.0, type="InvalidType", tag="MockTag")
        self.assertIn("Invalid type 'InvalidType'. Allowed values are:", str(context.exception))

    def test_timestamp_is_recent(self):
        """ Test that the default timestamp is close to the current time """
        now = datetime.now(timezone.utc)
        attr = AssetAttribute(value="abc", type="Events", tag="MockTag")

        parsed_time = datetime.strptime(attr.timestamp, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)

        # Allow a small time difference (e.g., 1 second) due to execution time
        time_difference = abs((now - parsed_time).total_seconds())
        self.assertLess(time_difference, 1, f"Timestamp '{attr.timestamp}' is not recent (difference: {time_difference}s)")

    def test_override_timestamp(self):
        """ Test creating an AssetAttribute with a custom timestamp """
        custom_timestamp = "2025-03-10T12:00:00.123Z"
        attr = AssetAttribute(value=456, type="Events", tag="AnotherTag", timestamp=custom_timestamp)

        self.assertEqual(attr.value, 456)
        self.assertEqual(attr.type, "Events")
        self.assertEqual(attr.tag, "AnotherTag")
        self.assertEqual(attr.timestamp, custom_timestamp)
