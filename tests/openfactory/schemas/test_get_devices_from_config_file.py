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
                expected = {
                    'device1': {
                        'uuid': 'uuid1',
                        'node': 'node1',
                        'agent': {
                            'port': 8080,
                            'device_xml': 'xml1',
                            'adapter': {'ip': None, 'image': 'ofa/adapter', 'port': 9090, 'environment': None},
                            'deploy': {'replicas': 1, 'resources': None}
                            },
                        'runtime': None},
                    'device2': {
                        'uuid': 'uuid2',
                        'node': 'node2',
                        'agent': {
                            'port': 8081,
                            'device_xml': 'xml2',
                            'adapter': {'ip': '1.2.3.4', 'image': None, 'port': 9091, 'environment': None},
                            'deploy': {'replicas': 1, 'resources': None}
                            },
                        'runtime': {'agent': {'cpus': 2.0}, 'producer': {'cpus': 1.5}, 'adapter': {'cpus': 1.0}}
                        }
                    }
                self.assertEqual(devices_dict, expected)
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
