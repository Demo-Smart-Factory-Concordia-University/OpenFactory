import unittest
from unittest.mock import patch
from pydantic import ValidationError
from openfactory.schemas.apps import OpenFactoryAppsConfig, get_apps_from_config_file


class TestOpenFactoryAppsConfig(unittest.TestCase):
    """
    Unit tests for class OpenFactoryAppsConfig
    """

    def test_valid_config(self):
        """ Test a valid configuration """
        valid_config = {
            "apps": {
                "demo1": {
                    "uuid": "DEMO-APP",
                    "image": "demofact/demo1",
                    "environment": [
                        "KAFKA_BROKER=broker:9092",
                        "KSQL_URL=http://ksqldb-server:8088",
                    ],
                }
            }
        }

        config = OpenFactoryAppsConfig(**valid_config)
        self.assertEqual(config.apps["demo1"].uuid, "DEMO-APP")
        self.assertEqual(config.apps["demo1"].image, "demofact/demo1")
        self.assertIn("KAFKA_BROKER=broker:9092", config.apps["demo1"].environment)

    def test_missing_required_fields(self):
        """ Test missing required fields (uuid & image) """
        invalid_config = {
            "apps": {
                "demo1": {
                    "environment": ["KAFKA_BROKER=broker:9092"]
                }
            }
        }

        with self.assertRaises(ValidationError) as context:
            OpenFactoryAppsConfig(**invalid_config)

        self.assertIn("uuid", str(context.exception))
        self.assertIn("image", str(context.exception))

    def test_missing_apps_key(self):
        """ Test missing `apps` key"""
        invalid_config = {
            "devices": {
                "demo1": {
                    "uuid": "DEMO-APP",
                    "image": "demofact/demo1",
                    "environment": [
                        "KAFKA_BROKER=broker:9092",
                        "KSQL_URL=http://ksqldb-server:8088",
                    ],
                }
            }
        }

        with self.assertRaises(ValidationError) as context:
            OpenFactoryAppsConfig(**invalid_config)

        self.assertIn("apps", str(context.exception))

    def test_invalid_environment_type(self):
        """ Test invalid environment type (string instead of list) """
        invalid_config = {
            "apps": {
                "demo1": {
                    "uuid": "DEMO-APP",
                    "image": "demofact/demo1",
                    "environment": "KAFKA_BROKER=broker:9092"
                }
            }
        }

        with self.assertRaises(ValidationError) as context:
            OpenFactoryAppsConfig(**invalid_config)

        self.assertIn("environment", str(context.exception))

    def test_optional_environment(self):
        """ Test environment field is optional """
        valid_config = {
            "apps": {
                "demo1": {
                    "uuid": "DEMO-APP",
                    "image": "demofact/demo1"
                }
            }
        }

        config = OpenFactoryAppsConfig(**valid_config)
        self.assertIsNone(config.apps["demo1"].environment)

    @patch("openfactory.schemas.apps.load_yaml", return_value={"invalid": "data"})
    @patch("openfactory.models.user_notifications.user_notify.fail")
    def test_invalid_yaml_file(self, mock_notify, mock_load_yaml):
        """ Test invalid YAML file handling """
        result = get_apps_from_config_file("dummy_path.yaml")
        self.assertIsNone(result)
        mock_notify.assert_called_once()
        self.assertIn("invalid format", mock_notify.call_args[0][0])

    @patch("openfactory.schemas.apps.load_yaml")
    def test_valid_yaml_file(self, mock_load_yaml):
        """ Test a valid YAML file """
        mock_load_yaml.return_value = {
            "apps": {
                "demo1": {
                    "uuid": "DEMO-APP",
                    "image": "demofact/demo1",
                    "environment": ["KAFKA_BROKER=broker:9092"]
                }
            }
        }

        result = get_apps_from_config_file("valid_config.yaml")
        self.assertIsNotNone(result)
        self.assertIn("demo1", result)
        self.assertEqual(result["demo1"]["uuid"], "DEMO-APP")
        self.assertEqual(result["demo1"]["image"], "demofact/demo1")
        self.assertIn("KAFKA_BROKER=broker:9092", result["demo1"]["environment"])
