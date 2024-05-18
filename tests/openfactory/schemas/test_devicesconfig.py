import unittest
from pydantic import ValidationError
from openfactory.schemas.devices import DevicesConfig


class TestDevicesConfig(unittest.TestCase):
    """
    Unit tests for class DevicesConfig
    """

    def test_validate_devices_valid(self):
        """
        Test case where devices have valid configurations
        """
        devices_data = {
            "device1": {
                "uuid": "uuid1",
                "node": "node1",
                "agent": {
                    "port": 8080,
                    "device_xml": "xml1",
                    "adapter": {"image": "ofa/adapter", "port": 9090}
                }
            },
            "device2": {
                "uuid": "uuid2",
                "node": "node2",
                "agent": {
                    "port": 8081,
                    "device_xml": "xml2",
                    "adapter": {"ip": "1.2.3.4", "port": 9091}
                },
                "runtime": {
                    "agent": {"cpus": 2.0},
                    "producer": {"cpus": 1.5},
                    "adapter": {"cpus": 1.0}
                }
            }
        }
        devices_config = DevicesConfig(devices=devices_data)
        self.assertIsNone(devices_config.validate_devices())

    def test_mandatory_fields(self):
        """
        Test all mandatory fields are enforced in schema
        """
        devices_data = {
            "devices": {
                "device1": {
                    # All mandatory fields are missing
                }
            }
        }
        with self.assertRaises(ValidationError) as context:
            DevicesConfig(devices=devices_data)
            # Check which mandatory fields are missing
            missing_fields = context.exception.errors()[0]['loc']
            self.assertIn("devices", missing_fields)
            self.assertIn("device1", missing_fields)
            self.assertIn("node", missing_fields)
            self.assertIn("agent", missing_fields)
            self.assertIn("port", missing_fields)
            self.assertIn("device_xml", missing_fields)
            self.assertIn("adapter", missing_fields)
            self.assertIn("port", missing_fields)

    def test_validate_devices_invalid_adapter(self):
        """
        Test adapter has either ip or imag defined
        """
        devices_data = {
            "device1": {
                "uuid": "uuid1",
                "node": "node1",
                "agent": {
                    "port": 8080,
                    "device_xml": "xml1",
                    "adapter": {"port": 7878}  # missing ip or image
                }
            }
        }

        devices_config = DevicesConfig(devices=devices_data)
        self.assertRaises(ValueError, devices_config.validate_devices)

        # both ip and image defined for adapter
        devices_data = {
            "device1": {
                "uuid": "uuid1",
                "node": "node1",
                "agent": {
                    "port": 8080,
                    "device_xml": "xml1",
                    "adapter": {
                        "ip": "1.2.3.4",
                        "image": "ofa/adapter",
                        "port": 7878
                        }
                }
            }
        }

        devices_config = DevicesConfig(devices=devices_data)
        self.assertRaises(ValueError, devices_config.validate_devices)
