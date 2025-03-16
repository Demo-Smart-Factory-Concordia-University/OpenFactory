import os
from unittest import TestCase
from unittest.mock import patch
from click.testing import CliRunner
import openfactory.ofa as ofa


@patch("openfactory.ofa.device.up.deploy_devices_from_config_file")
class TestDeviceUp(TestCase):
    """
    Unit tests for ofa.device.click_up
    """

    def test_device_up(self, mock_deploy_devices_from_config_file):
        """
        Test deploy_devices_from_config_file called correctly
        """
        runner = CliRunner()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/mock_agents.yml')
        result = runner.invoke(ofa.device.click_up, [config_file])
        mock_deploy_devices_from_config_file.assert_called_once_with(config_file)
        self.assertEqual(result.exit_code, 0)

    def test_device_up_none_existent_file(self, *args):
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
