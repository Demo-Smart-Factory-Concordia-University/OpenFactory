import os
from unittest import TestCase
from unittest.mock import patch
from click.testing import CliRunner
import openfactory.ofa as ofa


@patch("openfactory.ofa.nodes.down.remove_infrastack")
class TestNodesDown(TestCase):
    """
    Unit tests for ofa.nodes.down
    """

    def test_node_down(self, mock_remove_infrastack):
        """
        Test remove_infrastack called correctly
        """
        runner = CliRunner()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/base_infra_mock.yml')
        result = runner.invoke(ofa.nodes.click_down, [config_file])
        mock_remove_infrastack.assert_called_once_with(config_file)
        self.assertEqual(result.exit_code, 0)

    def test_node_down_none_existent_file(self, *args):
        """
        Test ofa.nodes.click_down with none exisitng config file
        """
        runner = CliRunner()
        result = runner.invoke(ofa.nodes.click_down, ['/does/not/exist/config_file.yml'])
        expect = ("Usage: down [OPTIONS] YAML_CONFIG_FILE\n"
                  "Try 'down --help' for help.\n"
                  "\n"
                  "Error: Invalid value for 'YAML_CONFIG_FILE': Path '/does/not/exist/config_file.yml' does not exist.\n")
        self.assertEqual(result.output, expect)
