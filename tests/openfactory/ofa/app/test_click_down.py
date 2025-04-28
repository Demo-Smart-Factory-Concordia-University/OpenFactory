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
    @patch("openfactory.ofa.app.down.process_yaml_files")
    def test_app_down(self, mock_process_yaml_files, mock_openfactory_manager):
        """
        Test shut_down_apps_from_config_file called correctly
        """
        mock_instance = MagicMock()
        mock_openfactory_manager.return_value = mock_instance

        runner = CliRunner()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/mock_apps.yml')
        result = runner.invoke(ofa.app.click_down, [config_file, '--dry-run'])
        mock_process_yaml_files.assert_called_once_with(config_file, True,
                                                        action_func=mock_instance.shut_down_apps_from_config_file,
                                                        action_name="shut down",
                                                        pattern='app_*.yml')
        self.assertEqual(result.exit_code, 0)

    def test_app_down_none_existent_file(self):
        """
        Test ofa.app.click_down with non-existing config file
        """
        runner = CliRunner()
        result = runner.invoke(ofa.app.click_down, ['/does/not/exist/config_file.yml'])
        expect = ("Usage: down [OPTIONS] PATH\n"
                  "Try 'down --help' for help.\n"
                  "\n"
                  "Error: Invalid value for 'PATH': Path '/does/not/exist/config_file.yml' does not exist.\n")
        self.assertEqual(result.output, expect)
        self.assertEqual(result.exit_code, 2)
