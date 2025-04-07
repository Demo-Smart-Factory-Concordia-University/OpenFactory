import unittest
from unittest.mock import patch, MagicMock
from openfactory.factories import shut_down_devices_from_config_file


class TestShutDownDevices(unittest.TestCase):
    """
    Test shut_down_devices_from_config_file
    """

    @patch('openfactory.factories.shut_down_devices.ksql')
    @patch('openfactory.factories.shut_down_devices.user_notify')
    @patch('openfactory.factories.shut_down_devices.OpenFactoryManager')
    @patch('openfactory.factories.shut_down_devices.get_devices_from_config_file')
    def test_shut_down_devices_normal_flow(
        self, mock_get_devices, mock_ofa_cls, mock_user_notify, mock_ksql
    ):
        """ Test shut_down_devices_from_config_file for normal case """
        # Mock YAML config result
        mock_get_devices.return_value = {
            'device1': {'uuid': 'UUID-123'},
            'device2': {'uuid': 'UUID-999'},
        }

        # Mock the OpenFactoryManager instance and its .devices() output
        mock_device_1 = MagicMock()
        mock_device_1.asset_uuid = 'UUID-123'

        mock_ofa = MagicMock()
        mock_ofa.devices.return_value = [mock_device_1]
        mock_ofa_cls.return_value = mock_ofa

        shut_down_devices_from_config_file('config.yaml')

        mock_get_devices.assert_called_once_with('config.yaml')

        # Check notify messages
        mock_user_notify.info.assert_any_call('device1:')
        mock_user_notify.info.assert_any_call('device2:')
        mock_user_notify.info.assert_any_call('No device UUID-999 deployed in OpenFactory')

        # Check correct device shutdown
        mock_ofa.tear_down_device.assert_called_once_with('UUID-123')

        # Ensure we didn’t try to shut down a non-deployed device
        called_uuids = [call[0][0] for call in mock_ofa.tear_down_device.call_args_list]
        assert 'UUID-999' not in called_uuids

    @patch('openfactory.factories.shut_down_devices.ksql')
    @patch('openfactory.factories.shut_down_devices.user_notify')
    @patch('openfactory.factories.shut_down_devices.OpenFactoryManager')
    @patch('openfactory.factories.shut_down_devices.get_devices_from_config_file')
    def test_shut_down_devices_none_config(
        self, mock_get_devices, mock_ofa_cls, mock_user_notify, mock_ksql
    ):
        """ Test case where yaml_config_file contains no devices """
        mock_get_devices.return_value = None

        shut_down_devices_from_config_file('empty.yaml')

        mock_get_devices.assert_called_once_with('empty.yaml')
        mock_ofa_cls.assert_not_called()
        mock_user_notify.info.assert_not_called()
