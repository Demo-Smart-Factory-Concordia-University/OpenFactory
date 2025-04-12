import unittest
from unittest.mock import patch, MagicMock
from openfactory.factories import shut_down_apps_from_config_file


class TestShutDownApps(unittest.TestCase):
    """
    Test shut_down_apps_from_config_file
    """

    @patch('openfactory.factories.shut_down_apps.user_notify')
    @patch('openfactory.factories.shut_down_apps.OpenFactoryManager')
    @patch('openfactory.factories.shut_down_apps.get_apps_from_config_file')
    def test_shut_down_apps_normal_flow(self, mock_get_apps, mock_ofa_cls, mock_user_notify):
        """ Test shut_down_apps_from_config_file for normal case """
        # Simulated app config from YAML
        mock_get_apps.return_value = {
            'app1': {'uuid': 'UUID-123'},
            'app2': {'uuid': 'UUID-456'},
        }

        # Mock the OpenFactoryManager instance and its behavior
        mock_ofa = MagicMock()
        mock_ofa.applications_uuid.return_value = ['UUID-123']
        mock_ofa_cls.return_value = mock_ofa

        shut_down_apps_from_config_file('dummy.yaml', ksqlClient=MagicMock())

        mock_get_apps.assert_called_once_with('dummy.yaml')
        mock_user_notify.info.assert_any_call('app1:')
        mock_user_notify.info.assert_any_call('app2:')
        mock_user_notify.info.assert_any_call('No application UUID-456 deployed in OpenFactory')
        mock_ofa.tear_down_application.assert_called_once_with('UUID-123')

        # app2 should not be shut down
        called_args = [call[0][0] for call in mock_ofa.tear_down_application.call_args_list]
        assert 'UUID-456' not in called_args

    @patch('openfactory.factories.shut_down_apps.user_notify')
    @patch('openfactory.factories.shut_down_apps.OpenFactoryManager')
    @patch('openfactory.factories.shut_down_apps.get_apps_from_config_file')
    def test_shut_down_apps_none_config(self, mock_get_apps, mock_ofa_cls, mock_user_notify):
        """ Test case where yaml_config_file contains no applications """
        mock_get_apps.return_value = None

        shut_down_apps_from_config_file('dummy.yaml', ksqlClient=MagicMock())

        mock_get_apps.assert_called_once_with('dummy.yaml')
        mock_ofa_cls.assert_not_called()
        mock_user_notify.info.assert_not_called()
