import unittest
import yaml
import os
from unittest.mock import patch
from tempfile import NamedTemporaryFile
from importlib import reload
import openfactory.schemas.devices as devices
from openfactory.schemas.devices import get_devices_from_config_file
from openfactory.schemas.uns import UNSSchema


class TestInfluxDB(unittest.TestCase):
    """
    Unit tests for class InfluxDB
    """

    @patch("openfactory.config.INFLUXDB_URL", "http://mock-url")
    @patch("openfactory.config.INFLUXDB_TOKEN", "mock-token")
    def test_default_values(self, *args):
        """
        Test if class InfluxDB assigns default values from config module
        """
        reload(devices)
        from openfactory.schemas.devices import InfluxDB
        influx_db = InfluxDB()

        self.assertEqual(influx_db.url, "http://mock-url")
        self.assertEqual(influx_db.token, "mock-token")
        self.assertIsNone(influx_db.organisation)
        self.assertIsNone(influx_db.bucket)

    @patch("openfactory.config.INFLUXDB_URL", "http://mock-url")
    @patch("openfactory.config.INFLUXDB_TOKEN", None)
    def test_missing_token(self, *args):
        """
        Test when token is missing or None in config and not provided explicitly
        """
        reload(devices)
        from openfactory.schemas.devices import InfluxDB
        with self.assertRaises(ValueError) as context:
            InfluxDB()
        self.assertTrue("Configuration error: 'token' is not provided, and 'INFLUXDB_TOKEN' is not defined in openfactory.config" in str(context.exception))

        # test case when INFLUXDB_TOKEN was never defined in config module
        delattr(devices.config, 'INFLUXDB_TOKEN')
        reload(devices)
        with self.assertRaises(ValueError) as context:
            InfluxDB()
        self.assertTrue("Configuration error: 'token' is not provided, and 'INFLUXDB_TOKEN' is not defined in openfactory.config" in str(context.exception))

    @patch("openfactory.config.INFLUXDB_URL", None)
    @patch("openfactory.config.INFLUXDB_TOKEN", "mock-token")
    def test_missing_url(self, *args):
        """
        Test when url is missing or None in config and not provided explicitly
        """
        reload(devices)
        from openfactory.schemas.devices import InfluxDB
        with self.assertRaises(ValueError) as context:
            InfluxDB()
        self.assertTrue("Configuration error: 'url' is not provided, and 'INFLUXDB_URL' is not defined in openfactory.config" in str(context.exception))

        # test case when INFLUXDB_TOKEN was never defined in config module
        delattr(devices.config, 'INFLUXDB_URL')
        reload(devices)
        with self.assertRaises(ValueError) as context:
            InfluxDB()
        self.assertTrue("Configuration error: 'url' is not provided, and 'INFLUXDB_URL' is not defined in openfactory.config" in str(context.exception))


class TestGetDevicesFromConfigFile(unittest.TestCase):
    """
    Unit tests for get_devices_from_config_file function
    """

    def setUp(self):
        # Define a valid UNS schema
        self.schema_data = {
            "namespace_structure": [
                {"inc": "OpenFactory"},
                {"workcenter": ["WC1", "WC2"]},
                {"asset": "ANY"},
                {"attribute": "ANY"}
            ],
            "uns_template": "inc/workcenter/asset/attribute"
        }

        # Write to temporary YAML file
        self.uns_schema_file = NamedTemporaryFile(mode="w+", delete=False)
        yaml.dump(self.schema_data, self.uns_schema_file)
        self.uns_schema_file.close()

        # Load actual UNSSchema instance
        self.uns_schema = UNSSchema(schema_yaml_file=self.uns_schema_file.name)

    def tearDown(self):
        os.remove(self.uns_schema_file.name)

    @patch("openfactory.config.INFLUXDB_URL", "http://mock-url")
    @patch("openfactory.config.INFLUXDB_TOKEN", "mock-token")
    def test_get_devices_from_config_file_valid(self, *args):
        """
        Test case where YAML configuration file is valid
        """
        reload(devices)

        devices_yaml_data = {
            "devices": {
                "device1": {
                    "uuid": "uuid1",
                    "workcenter": "WC2",
                    "asset": "cnc",
                    "agent": {
                        "port": 8080,
                        "device_xml": "xml1",
                        "adapter": {"image": "ofa/adapter", "port": 9090}
                    },
                    "ksql_tables": [],
                },
                "device2": {
                    "uuid": "uuid2",
                    "agent": {
                        "port": 8081,
                        "device_xml": "xml2",
                        "adapter": {"ip": "1.2.3.4", "port": 9091},
                        "deploy": {"replicas": 3,
                                   "resources": {"reservations": {"cpus": 2}, "limits": {"cpus": 4}},
                                   "placement": {"constraints": ["type=ofa", "zone=factory1"]}},
                    }
                },
                "device3": {
                    "uuid": "uuid3",
                    "asset": "cnc3",
                    "agent": {
                        "port": 8082,
                        "device_xml": "xml3",
                        "adapter": {"ip": "1.2.3.4", "port": 9092,
                                    "deploy": {"replicas": 3, "resources": {"reservations": {"cpus": 2}, "limits": {"cpus": 4}}}},
                    },
                    "influxdb": {},
                }
            }
        }

        with NamedTemporaryFile(mode='w') as temp_file:
            yaml.dump(devices_yaml_data, temp_file)
            temp_file.seek(0)
            with patch("openfactory.schemas.devices.user_notify") as mock_user_notify:
                devices_dict = get_devices_from_config_file(temp_file.name, self.uns_schema)
                expected = {
                    'device1': {
                        'uuid': 'uuid1',
                        'agent': {
                            "ip": None,
                            'port': 8080,
                            'device_xml': 'xml1',
                            'adapter': {'ip': None, 'image': 'ofa/adapter', 'port': 9090, 'environment': None, 'deploy': None},
                            'deploy': {'replicas': 1, 'resources': None, 'placement': None}
                            },
                        'supervisor': None,
                        'ksql_tables': [],
                        'influxdb': None,
                        "uns": {
                            "levels": {
                                "inc": "OpenFactory",
                                "workcenter": "WC2",
                                "asset": "cnc"
                            },
                            "uns_id": "OpenFactory/WC2/cnc"
                            }
                        },
                    'device2': {
                        'uuid': 'uuid2',
                        'agent': {
                            "ip": None,
                            'port': 8081,
                            'device_xml': 'xml2',
                            'adapter': {'ip': '1.2.3.4', 'image': None, 'port': 9091, 'environment': None, 'deploy': None},
                            'deploy': {'replicas': 3,
                                       'resources': {'reservations': {'cpus': 2.0, 'memory': None}, 'limits': {'cpus': 4.0, 'memory': None}},
                                       'placement': {'constraints': ["type=ofa", "zone=factory1"]}},
                            },
                        'supervisor': None,
                        'ksql_tables': None,
                        'influxdb': None,
                        "uns": {
                            "levels": {
                                "inc": "OpenFactory",
                                "asset": "uuid2"
                            },
                            "uns_id": "OpenFactory/uuid2"
                            }
                        },
                    'device3': {
                        'uuid': 'uuid3',
                        'agent': {
                            "ip": None,
                            'port': 8082,
                            'device_xml': 'xml3',
                            'adapter': {'ip': '1.2.3.4', 'image': None, 'port': 9092, 'environment': None,
                                        'deploy': {'replicas': 3,
                                                   'resources': {'reservations': {'cpus': 2.0, 'memory': None}, 'limits': {'cpus': 4.0, 'memory': None}},
                                                   'placement': None}},
                            'deploy': {'replicas': 1, 'resources': None, 'placement': None}
                            },
                        'supervisor': None,
                        'ksql_tables': None,
                        'influxdb': {'url': 'http://mock-url', 'organisation': None, 'token': 'mock-token', 'bucket': None},
                        "uns": {
                            "levels": {
                                "inc": "OpenFactory",
                                "asset": "cnc3"
                            },
                            "uns_id": "OpenFactory/cnc3"
                            }
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
                devices_dict = get_devices_from_config_file(temp_file.name, self.uns_schema)
                self.assertIsNone(devices_dict)
                mock_user_notify.fail.assert_called()
