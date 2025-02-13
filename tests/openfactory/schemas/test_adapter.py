import unittest
from openfactory.schemas.devices import Adapter


class TestAdapter(unittest.TestCase):
    """
    Unit tests for class Adapter
    """

    def test_valid_adapter(self):
        """
        Test valid Adapter
        """
        data = {
            "ip": "10.0.0.1",
            "port": 7878,
        }

        mod = Adapter(**data)

        # Check no exception is raised and the model is correctly populated
        self.assertEqual(mod.ip, "10.0.0.1")
        self.assertEqual(mod.port, 7878)
        self.assertIsNone(mod.image)
        self.assertIsNone(mod.environment)
        self.assertIsNone(mod.deploy)

    def test_adapter_image(self):
        """
        Test adapter image field
        """
        data = {
            "image": "adapter_image",
            "port": 7878,
        }

        mod = Adapter(**data)

        # Check no exception is raised and the model is correctly populated
        self.assertEqual(mod.image, "adapter_image")
        self.assertEqual(mod.port, 7878)
        self.assertIsNone(mod.ip)
        self.assertIsNone(mod.environment)
        self.assertIsNone(mod.deploy)

    def test_adapter_ip_and_image(self):
        """
        Test error raised if adapter IP and image are both defined
        """
        data = {
            "ip": "10.0.0.1",
            "image": "adapter_image",
            "port": 7878,
        }

        with self.assertRaises(ValueError) as context:
            Adapter(**data)

        # Check error message
        self.assertIn("Either 'ip' or 'image' must be specified in the adapter.", str(context.exception))

    def test_adapter_environment(self):
        """
        Test adapter environment field
        """
        data = {
            "image": "adapter_image",
            "port": 7878,
            "environment": ['var1=toto', 'var2=titi']
        }

        mod = Adapter(**data)

        # Check no exception is raised and the model is correctly populated
        self.assertEqual(mod.image, "adapter_image")
        self.assertEqual(mod.port, 7878)
        self.assertEqual(mod.environment, ['var1=toto', 'var2=titi'])
        self.assertIsNone(mod.ip)
        self.assertIsNone(mod.deploy)
