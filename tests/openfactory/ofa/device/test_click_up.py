import os
from unittest import TestCase
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import openfactory.ofa as ofa


class TestDeviceUp(TestCase):
    """
    Unit tests for ofa.device.click_up
    """

    @patch("openfactory.ofa.device.up.OpenFactoryManager")
    def test_device_up(self, mock_openfactory_manager):
        """
        Test deploy_devices_from_config_file called correctly
        """
        mock_instance = MagicMock()
        mock_openfactory_manager.return_value = mock_instance

        runner = CliRunner()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/mock_devices.yml')
        result = runner.invoke(ofa.device.click_up, [config_file])
        mock_instance.deploy_devices_from_config_file.assert_called_once_with(config_file)
        self.assertEqual(result.exit_code, 0)

    def test_device_up_none_existent_file(self):
        """
        Test ofa.device.click_up with none exisitng config file
        """
        runner = CliRunner()
        result = runner.invoke(ofa.device.click_up, ['/does/not/exist/config_file.yml'])
        expect = ("Usage: up [OPTIONS] YAML_CONFIG_FILE\n"
                  "Try 'up --help' for help.\n"
                  "\n"
                  "Error: Invalid value for 'YAML_CONFIG_FILE': Path '/does/not/exist/config_file.yml' does not exist.\n")
        self.assertEqual(result.output, expect)
