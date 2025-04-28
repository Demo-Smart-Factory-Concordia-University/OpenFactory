import os
from unittest import TestCase
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import openfactory.ofa as ofa


class TestAppDown(TestCase):
    """
    Unit tests for ofa.app.click_down
    """

    @patch("openfactory.ofa.app.down.OpenFactoryManager")
    def test_app_down(self, mock_openfactory_manager):
        """
        Test shut_down_apps_from_config_file called correctly
        """
        mock_instance = MagicMock()
        mock_openfactory_manager.return_value = mock_instance

        runner = CliRunner()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/mock_apps.yml')
        result = runner.invoke(ofa.app.click_down, [config_file])
        mock_instance.shut_down_apps_from_config_file.assert_called_once_with(config_file)
        self.assertEqual(result.exit_code, 0)

    def test_app_down_none_existent_file(self):
        """
        Test ofa.app.click_down with non-existing config file
        """
        runner = CliRunner()
        result = runner.invoke(ofa.app.click_down, ['/does/not/exist/config_file.yml'])
        expect = ("Usage: down [OPTIONS] YAML_CONFIG_FILE\n"
                  "Try 'down --help' for help.\n"
                  "\n"
                  "Error: Invalid value for 'YAML_CONFIG_FILE': Path '/does/not/exist/config_file.yml' does not exist.\n")
        self.assertEqual(result.output, expect)
