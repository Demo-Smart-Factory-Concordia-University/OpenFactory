import unittest
import sys
from unittest.mock import patch
from openfactory.ofacli import init_environment, main
from openfactory.kafka.ksql import KSQLDBClientException


class TestOFAEntryPoint(unittest.TestCase):
    """ Unit tests for OpenFactory ofacli.py entrypoint """

    @patch('openfactory.ofacli.ksql.connect')
    @patch('openfactory.ofacli.dal.connect')
    @patch('openfactory.ofacli.user_notify.setup')
    def test_init_environment_success(self, mock_notify, mock_dal_connect, mock_ksql_connect):
        """ init_environment returns True on successful setup """
        mock_ksql_connect.return_value = None

        result = init_environment()

        self.assertTrue(result)
        mock_notify.assert_called_once()
        mock_dal_connect.assert_called_once()
        mock_ksql_connect.assert_called_once()

    @patch('openfactory.ofacli.ksql.connect', side_effect=KSQLDBClientException("Connection failed"))
    @patch('openfactory.ofacli.dal.connect')
    @patch('openfactory.ofacli.user_notify')
    def test_init_environment_failure(self, mock_notify, mock_dal_connect, mock_ksql_connect):
        """ init_environment returns False if ksql.connect fails """
        result = init_environment()

        self.assertFalse(result)
        mock_notify.fail.assert_called_once_with('Failed to connect to ksqlDB server')

    @patch('openfactory.ofacli.cli')
    @patch('openfactory.ofacli.init_environment', return_value=True)
    def test_main_runs_cli_if_env_init_ok(self, mock_init_env, mock_cli):
        """ main() calls cli() if init_environment() is successful """
        main()

        mock_init_env.assert_called_once()
        mock_cli.assert_called_once()

    @patch('openfactory.ofacli.init_environment', return_value=False)
    @patch('openfactory.ofacli.exit', side_effect=SystemExit(1))
    def test_main_exits_on_failed_env_init(self, mock_exit, mock_init_env):
        """ main() exits if init_environment() fails """
        with patch.object(sys, 'argv', ['ofa']):
            with self.assertRaises(SystemExit) as cm:
                main()

            mock_init_env.assert_called_once()
            mock_exit.assert_called_once_with(1)
            self.assertEqual(cm.exception.code, 1)
