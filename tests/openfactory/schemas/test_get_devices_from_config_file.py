import unittest
from unittest.mock import patch
from tempfile import NamedTemporaryFile
import yaml
from openfactory.schemas.devices import get_devices_from_config_file


class TestGetDevicesFromConfigFile(unittest.TestCase):
    """
    Unit tests for get_devices_from_config_file function
    """

    def test_get_devices_from_config_file_valid(self):
        """
        Test case where YAML configuration file is valid
        """
        devices_yaml_data = {
            "devices": {
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
        }

        with NamedTemporaryFile(mode='w') as temp_file:
            yaml.dump(devices_yaml_data, temp_file)
            temp_file.seek(0)
            with patch("openfactory.schemas.devices.user_notify") as mock_user_notify:
                devices_dict = get_devices_from_config_file(temp_file.name)
                # add fields that will be added by get_devices_from_config_file
                devices_yaml_data["devices"]["device1"]["agent"]["adapter"]["ip"] = None
                devices_yaml_data["devices"]["device1"]["agent"]["adapter"]["environment"] = None
                devices_yaml_data["devices"]["device1"]["runtime"] = None
                devices_yaml_data["devices"]["device2"]["agent"]["adapter"]["image"] = None
                devices_yaml_data["devices"]["device2"]["agent"]["adapter"]["environment"] = None
                self.assertEqual(devices_dict, devices_yaml_data["devices"])
                mock_user_notify.fail.assert_not_called()

    def test_get_devices_from_config_file_invalid(self):
        """
        Test case where YAML configuration file is invalid
        """
        devices_yaml_data = {
            "devices": {
                "device1": {
                    "uuid": "uuid1",
                    "node": "node1",
                    "agent": {
                        "port": 8080,
                        "device_xml": "xml1",
                        "adapter": {}  # Missing 'port'
                    }
                }
            }
        }

        with NamedTemporaryFile(mode='w') as temp_file:
            yaml.dump(devices_yaml_data, temp_file)
            temp_file.seek(0)
            with patch("openfactory.schemas.devices.user_notify") as mock_user_notify:
                devices_dict = get_devices_from_config_file(temp_file.name)
                self.assertIsNone(devices_dict)
                mock_user_notify.fail.assert_called()
