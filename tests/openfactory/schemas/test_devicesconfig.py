import unittest
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

    def test_validate_devices_invalid_adapter(self):
        """
        Test adapter has either ip or image defined
        """
        devices_data = {
            "device1": {
                "uuid": "uuid1",
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

        # both ip and adapter defiend for agent
        devices_data = {
            "device1": {
                "uuid": "uuid1",
                "agent": {
                    "ip": "10.0.0.1",
                    "port": 8080,
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

        # both ip and device_xml defiend for agent
        devices_data = {
            "device1": {
                "uuid": "uuid1",
                "agent": {
                    "ip": "10.0.0.1",
                    "port": 8080,
                    "device_xml": "xml1",
                }
            }
        }

        devices_config = DevicesConfig(devices=devices_data)
        self.assertRaises(ValueError, devices_config.validate_devices)

    def test_agent_resources(self):
        """
        Test agent resources
        """
        devices_data = {
            "device1": {
                "uuid": "uuid1",
                "node": "node1",
                "agent": {
                    "port": 8081,
                    "device_xml": "xml1",
                    "adapter": {"ip": "1.2.3.4", "port": 9091},
                    "deploy": {"resources": {
                        "reservations": {"cpus": 3},
                        "limits": {"cpus": 5}
                    }},
                }
            },
            "device2": {
                "uuid": "uuid1",
                "node": "node1",
                "agent": {
                    "port": 8082,
                    "device_xml": "xml2",
                    "adapter": {"ip": "1.2.3.5", "port": 9091},
                }
            }
        }
        devices_config = DevicesConfig(devices=devices_data)
        self.assertEqual(devices_config.devices['device1'].agent.deploy.resources.reservations.cpus, 3)
        self.assertEqual(devices_config.devices['device1'].agent.deploy.resources.limits.cpus, 5)
        self.assertEqual(devices_config.devices['device2'].agent.deploy.resources, None)

    def test_replicas(self):
        """
        Test that replicas
        """
        devices_data = {
            "device1": {
                "uuid": "uuid1",
                "node": "node1",
                "agent": {
                    "port": 8081,
                    "device_xml": "xml1",
                    "adapter": {"ip": "1.2.3.4", "port": 9091},
                    "deploy": {"replicas": 3},
                }
            },
            "device2": {
                "uuid": "uuid1",
                "node": "node1",
                "agent": {
                    "port": 8082,
                    "device_xml": "xml2",
                    "adapter": {"ip": "1.2.3.5", "port": 9091},
                }
            }
        }

        devices_config = DevicesConfig(devices=devices_data)
        self.assertEqual(devices_config.devices['device1'].agent.deploy.replicas, 3)
        # Test that replicas defaults to 1 in case it is not defined
        self.assertEqual(devices_config.devices['device2'].agent.deploy.replicas, 1)
