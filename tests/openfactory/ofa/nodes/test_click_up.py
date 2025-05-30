import os
from unittest import TestCase
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import openfactory.ofa as ofa


@patch("openfactory.ofa.nodes.up.OpenFactoryCluster")
class TestNodesUp(TestCase):
    """
    Unit tests for ofa.nodes.up
    """

    def test_node_up(self, mock_cluster_class):
        """
        Test create_infrastack called correctly
        """
        mock_cluster_instance = MagicMock()
        mock_cluster_class.return_value = mock_cluster_instance

        runner = CliRunner()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/base_infra_mock.yml')
        result = runner.invoke(ofa.nodes.click_up, [config_file])
        mock_cluster_instance.create_infrastack_from_config_file.assert_called_once_with(config_file)
        self.assertEqual(result.exit_code, 0)

    def test_node_up_none_existent_file(self, mock_create_infrastack):
        """
        Test ofa.nodes.click_up with none exisitng config file
        """
        runner = CliRunner()
        result = runner.invoke(ofa.nodes.click_up, ['/does/not/exist/config_file.yml'])
        expect = ("Usage: up [OPTIONS] YAML_CONFIG_FILE\n"
                  "Try 'up --help' for help.\n"
                  "\n"
                  "Error: Invalid value for 'YAML_CONFIG_FILE': Path '/does/not/exist/config_file.yml' does not exist.\n")
        self.assertEqual(result.output, expect)
