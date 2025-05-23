import unittest
from unittest.mock import patch
from click.testing import CliRunner
from openfactory.ofa.cli import cli


class TestCLI(unittest.TestCase):
    """
    Unit test OpenFactory CLI interface
    """

    def setUp(self):
        self.runner = CliRunner()

    def test_main_help_lists_all_command_groups(self):
        """ Test ofa help command """
        result = self.runner.invoke(cli, ['--help'])

        self.assertEqual(result.exit_code, 0)
        for command in ['config', 'nodes', 'agent', 'device', 'apps', 'asset']:
            self.assertIn(command, result.output)

    @patch('openfactory.ofa.nodes.up.click_up.callback')
    @patch('click.Path.convert', return_value='dummy.yml')
    def test_nodes_up_invoked(self, mock_convert, mock_up_callback):
        """ Test ofa nodes up command """
        result = self.runner.invoke(cli, ['nodes', 'up', 'dummy.yml'])
        self.assertEqual(result.exit_code, 0)
        mock_up_callback.assert_called_once_with(yaml_config_file='dummy.yml')

    @patch('openfactory.ofa.nodes.down.click_down.callback')
    @patch('click.Path.convert', return_value='dummy.yml')
    def test_nodes_down_invoked(self, mock_convert, mock_up_callback):
        """ Test ofa nodes down command """
        result = self.runner.invoke(cli, ['nodes', 'down', 'dummy.yml'])
        self.assertEqual(result.exit_code, 0)
        mock_up_callback.assert_called_once_with(yaml_config_file='dummy.yml')

    @patch('openfactory.ofa.config.ls.callback')
    def test_config_ls_invoked(self, mock_ls_callback):
        """ Test ofa nodes ls command """
        self.runner.invoke(cli, ['config', 'ls'])
        mock_ls_callback.assert_called_once()

    @patch('openfactory.ofa.agent.ls.ls.callback')
    def test_agent_ls_invoked(self, mock_agent_ls):
        """ Test ofa agent ls command """
        self.runner.invoke(cli, ['agent', 'ls'])
        mock_agent_ls.assert_called_once()

    @patch('openfactory.ofa.device.up.click_up.callback')
    @patch('click.Path.convert', return_value='dummy.yml')
    def test_device_up_invoked(self, mock_convert, mock_device_up):
        """ Test ofa device up command """
        result = self.runner.invoke(cli, ['device', 'up', 'dummy.yml'])
        self.assertEqual(result.exit_code, 0)
        mock_device_up.assert_called_once_with(path='dummy.yml', dry_run=False)

    @patch('openfactory.ofa.device.down.click_down.callback')
    @patch('click.Path.convert', return_value='dummy.yml')
    def test_device_down_invoked(self, mock_convert, mock_device_down):
        """ Test ofa device down command """
        result = self.runner.invoke(cli, ['device', 'down', 'dummy.yml'])
        self.assertEqual(result.exit_code, 0)
        mock_device_down.assert_called_once_with(path='dummy.yml', dry_run=False)

    @patch('openfactory.ofa.device.connect_to_influxdb.click_connect_influxdb.callback')
    @patch('click.Path.convert', return_value='dummy.yml')
    def test_device_connect_influxdb_invoked(self, mock_convert, mock_connect):
        """ Test ofa device connect-influxdb command """
        result = self.runner.invoke(cli, ['device', 'connect-influxdb', 'dummy.yml'])
        self.assertEqual(result.exit_code, 0)
        mock_connect.assert_called_once()

    @patch('openfactory.ofa.app.up.click_up.callback')
    @patch('click.Path.convert', return_value='dummy.yml')
    def test_apps_up_invoked(self, mock_convert, mock_apps_up):
        """ Test ofa apps up command """
        result = self.runner.invoke(cli, ['apps', 'up', 'dummy.yml'])
        self.assertEqual(result.exit_code, 0)
        mock_apps_up.assert_called_once_with(path='dummy.yml', dry_run=False)

    @patch('openfactory.ofa.app.down.click_down.callback')
    @patch('click.Path.convert', return_value='dummy.yml')
    def test_apps_down_invoked(self, mock_convert, mock_apps_down):
        """ Test ofa apps down command """
        result = self.runner.invoke(cli, ['apps', 'down', 'dummy.yml'])
        self.assertEqual(result.exit_code, 0)
        mock_apps_down.assert_called_once_with(path='dummy.yml', dry_run=False)

    @patch('openfactory.ofa.asset.register.callback')
    def test_asset_register_invoked(self, mock_register_callback):
        """ Test ofa asset register command """
        result = self.runner.invoke(cli, ['asset', 'register', 'uuid-123', 'robot'])

        self.assertEqual(result.exit_code, 0)
        mock_register_callback.assert_called_once_with(
            asset_uuid='uuid-123',
            asset_type='robot',
            docker_service=''
        )

    @patch('openfactory.ofa.asset.register.callback')
    def test_asset_register_with_docker_service(self, mock_register_callback):
        """ Test ofa asset register command with docker service """
        result = self.runner.invoke(cli, [
            'asset', 'register', 'uuid-123', 'robot', '--docker-service', 'my_service'
        ])

        self.assertEqual(result.exit_code, 0)
        mock_register_callback.assert_called_once_with(
            asset_uuid='uuid-123',
            asset_type='robot',
            docker_service='my_service'
        )

    @patch('openfactory.ofa.asset.deregister.callback')
    def test_asset_deregister_invoked(self, mock_deregister_callback):
        """ Test ofa asset deregister command """
        result = self.runner.invoke(cli, ['asset', 'deregister', 'uuid-123'])

        self.assertEqual(result.exit_code, 0)
        mock_deregister_callback.assert_called_once_with(asset_uuid='uuid-123')
