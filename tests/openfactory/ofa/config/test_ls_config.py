from unittest import TestCase
from unittest.mock import patch
from click.testing import CliRunner
from pathlib import Path
import openfactory.ofa as ofa
from openfactory import ROOT_DIR


class TestConfigLs(TestCase):
    """
    Unit tests for ofa.config.ls
    """

    @patch("openfactory.ofa.config.ls_config.load_yaml")
    def test_config_ls(self, mock_load_yaml):
        """
        Test shut_down_apps_from_config_file called correctly
        """
        fake_config = {'foo': 'bar', 'debug': True}
        mock_load_yaml.return_value = fake_config

        runner = CliRunner()
        result = runner.invoke(ofa.config.ls)

        expected_path = Path(ROOT_DIR) / 'config' / 'openfactory.yml'
        mock_load_yaml.assert_called_once_with(expected_path)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("foo = bar", result.output)
        self.assertIn("debug = True", result.output)
