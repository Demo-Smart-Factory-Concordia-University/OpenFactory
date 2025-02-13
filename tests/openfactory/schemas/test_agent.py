import unittest
from openfactory.schemas.devices import Agent


class TestAgent(unittest.TestCase):
    """
    Unit tests for class Agent
    """

    def test_valid_agent(self):
        """
        Test valid Agent
        """
        data = {
            "ip": "10.0.0.1",
            "port": 5000,
        }

        mod = Agent(**data)

        # Check no exception is raised and the model is correctly populated
        self.assertEqual(mod.ip, "10.0.0.1")
        self.assertEqual(mod.port, 5000)
        self.assertIsNone(mod.device_xml)
        self.assertIsNone(mod.adapter)
        self.assertIsNone(mod.deploy)

        data = {
            "port": 8080,
            "device_xml": "xml1",
            "adapter": {
                "ip": "1.2.3.4",
                "port": 7878
                }
        }

        mod = Agent(**data)

        # Check no exception is raised and the model is correctly populated
        self.assertEqual(mod.port, 8080)
        self.assertEqual(mod.device_xml, "xml1")
        self.assertIsNone(mod.deploy)

    def test_missing_device_xml(self):
        """
        Test error raised if device_xml missing
        """

        data = {
            "port": 5000,
            "adapter": {
                "ip": "1.2.3.4",
                "port": 7878
                }
        }

        with self.assertRaises(ValueError) as context:
            Agent(**data)

        # Check error message
        self.assertIn("'device_xml' is missing", str(context.exception))

    def test_missing_adapter(self):
        """
        Test error raised if adapter missing
        """

        data = {
            "port": 5000,
            "device_xml": "xml1",
        }

        with self.assertRaises(ValueError) as context:
            Agent(**data)

        # Check error message
        self.assertIn("'adapter' definition is missing", str(context.exception))

    def test_adapter_external_agent(self):
        """
        Test error raised if adapter is defined for an external agent
        """

        data = {
            "ip": "10.0.0.1",
            "port": 5000,
            "adapter": {
                "ip": "1.2.3.4",
                "port": 7878
                }
        }

        with self.assertRaises(ValueError) as context:
            Agent(**data)

        # Check error message
        self.assertIn("'adapter' can not be defined for an external agent", str(context.exception))

    def test_device_xml_external_agent(self):
        """
        Test error raised if device_xml is defined for an external agent
        """

        data = {
            "ip": "10.0.0.1",
            "port": 5000,
            "device_xml": "dev.xml"
        }

        with self.assertRaises(ValueError) as context:
            Agent(**data)

        # Check error message
        self.assertIn("'device_xml' can not be defined for an external agent", str(context.exception))
