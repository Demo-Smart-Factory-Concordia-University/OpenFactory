import os
from unittest import TestCase
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import openfactory.ofa as ofa


class TestDeviceDown(TestCase):
    """
    Unit tests for ofa.device.click_down
    """

    @patch("openfactory.ofa.device.down.OpenFactoryManager")
    def test_device_down(self, mock_openfactory_manager):
        """
        Test shut_down_devices_from_config_file called correctly
        """
        mock_instance = MagicMock()
        mock_openfactory_manager.return_value = mock_instance

        runner = CliRunner()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/mock_devices.yml')
        result = runner.invoke(ofa.device.click_down, [config_file])
        mock_instance.shut_down_devices_from_config_file.assert_called_once_with(config_file)
        self.assertEqual(result.exit_code, 0)

    def test_device_down_none_existent_file(self):
        """
        Test ofa.device.click_down with none exisitng config file
        """
        runner = CliRunner()
        result = runner.invoke(ofa.device.click_down, ['/does/not/exist/config_file.yml'])
        expect = ("Usage: down [OPTIONS] YAML_CONFIG_FILE\n"
                  "Try 'down --help' for help.\n"
                  "\n"
                  "Error: Invalid value for 'YAML_CONFIG_FILE': Path '/does/not/exist/config_file.yml' does not exist.\n")
        self.assertEqual(result.output, expect)
