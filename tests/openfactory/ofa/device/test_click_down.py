import inspect
import os
from unittest import TestCase
from unittest.mock import patch
from click.testing import CliRunner

import openfactory.ofa as ofa
from openfactory.ofa.ksqldb import ksql


class TestDeviceDown(TestCase):
    """
    Unit tests for ofa.device.click_down
    """

    def test_shut_down_devices_from_config_file_signature(self):
        """ Test if signature of deploy_devices_from_config_file did not change """
        from openfactory.factories import shut_down_devices_from_config_file
        sig = inspect.signature(shut_down_devices_from_config_file)

        expected_params = [
            inspect.Parameter("yaml_config_file", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter("ksqlClient", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ]

        actual_params = list(sig.parameters.values())
        self.assertEqual(len(actual_params), len(expected_params))

        for actual, expected in zip(actual_params, expected_params):
            self.assertEqual(actual.name, expected.name)
            self.assertEqual(actual.kind, expected.kind)
            self.assertEqual(actual.default, expected.default)
            self.assertEqual(actual.annotation, expected.annotation)

        # Check that there is no return annotation
        self.assertEqual(sig.return_annotation, inspect.Signature.empty)

    @patch("openfactory.ofa.device.down.shut_down_devices_from_config_file")
    def test_device_down(self, mock_shut_down_devices_from_config_file):
        """
        Test shut_down_devices_from_config_file called correctly
        """
        runner = CliRunner()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/mock_devices.yml')
        result = runner.invoke(ofa.device.click_down, [config_file])
        mock_shut_down_devices_from_config_file.assert_called_once_with(config_file, ksqlClient=ksql.client)
        self.assertEqual(result.exit_code, 0)

    @patch("openfactory.ofa.device.down.shut_down_devices_from_config_file")
    def test_device_down_none_existent_file(self, *args):
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
