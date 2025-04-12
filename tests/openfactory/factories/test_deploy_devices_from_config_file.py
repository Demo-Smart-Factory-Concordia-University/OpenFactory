import unittest
from unittest.mock import patch, MagicMock
from openfactory.factories import deploy_devices_from_config_file


class TestDeployDevicesFromConfigFile(unittest.TestCase):
    """
    Test deploy_devices_from_config_file
    """

    @patch("openfactory.factories.deploy_devices.get_devices_from_config_file")
    @patch("openfactory.factories.deploy_devices.OpenFactoryManager")
    @patch("openfactory.factories.deploy_devices.user_notify")
    @patch("openfactory.factories.deploy_devices.register_asset")
    def test_deploy_devices_successful(
        self, mock_register_asset, mock_user_notify,
        mock_open_factory_manager, mock_get_devices
    ):
        """ Test succesfull deploy of a device """

        mock_devices = {
            "Device1": {
                "uuid": "uuid-123",
                "agent": {
                    "ip": "",
                    "device_xml": "devices/device1.xml"
                },
                "ksql_tables": ["agent"],
                "supervisor": {"param": "value"}
            }
        }
        mock_get_devices.return_value = mock_devices

        mock_ofa = MagicMock()
        mock_ofa.devices_uuid.return_value = []  # UUID not present
        mock_open_factory_manager.return_value = mock_ofa

        mock_ksql_client = MagicMock()
        deploy_devices_from_config_file("/path/to/config.yaml", ksqlClient=mock_ksql_client)

        mock_user_notify.info.assert_any_call("Device1:")
        mock_register_asset.assert_called_once_with("uuid-123", "Device", ksqlClient=mock_ksql_client, docker_service="")
        mock_ofa.deploy_mtconnect_agent.assert_called_once_with(device_uuid="uuid-123",
                                                                device_xml_uri="/path/to/devices/device1.xml",
                                                                agent=mock_devices["Device1"]["agent"])
        mock_ofa.deploy_kafka_producer.assert_called_once_with(mock_devices["Device1"])
        mock_ofa.create_device_ksqldb_tables.assert_called_once()
        mock_ofa.deploy_device_supervisor.assert_called_once()
        mock_user_notify.success.assert_called_once_with("Device uuid-123 deployed successfully")

    @patch("openfactory.factories.deploy_devices.get_devices_from_config_file")
    @patch("openfactory.factories.deploy_devices.OpenFactoryManager")
    def test_no_devices_loaded(self, mock_get_devices, mock_open_factory_manager):
        """ Test case when no device in yaml_config_file """
        mock_get_devices.return_value = None
        mock_ofa = MagicMock()
        mock_open_factory_manager.return_value = mock_ofa
        result = deploy_devices_from_config_file("/path/to/config.yaml", ksqlClient=MagicMock())

        self.assertIsNone(result)  # Should exit early with no error
        mock_ofa.deploy_mtconnect_agent.assert_not_called()
        mock_ofa.deploy_kafka_producer.assert_not_called()
        mock_ofa.create_device_ksqldb_tables.assert_not_called()
        mock_ofa.deploy_device_supervisor.assert_not_called()

    @patch("openfactory.factories.deploy_devices.get_devices_from_config_file")
    @patch("openfactory.factories.deploy_devices.OpenFactoryManager")
    @patch("openfactory.factories.deploy_devices.user_notify")
    def test_device_already_exists(self, mock_user_notify, mock_open_factory_manager, mock_get_devices):
        """ Test case where device is already deployed """

        mock_devices = {
            "Device2": {
                "uuid": "uuid-xyz",
                "agent": {
                    "ip": "192.168.1.10",  # IP is present so XML URI path not needed
                    "device_xml": ""
                },
                "ksql_tables": [],
                "supervisor": None
            }
        }
        mock_get_devices.return_value = mock_devices
        mock_ofa = MagicMock()
        mock_ofa.devices_uuid.return_value = ["uuid-xyz"]
        mock_open_factory_manager.return_value = mock_ofa

        deploy_devices_from_config_file("/config.yml", ksqlClient=MagicMock())

        mock_user_notify.info.assert_any_call("Device2:")
        mock_user_notify.info.assert_any_call("Device uuid-xyz exists already and was not deployed")
        mock_ofa.deploy_mtconnect_agent.assert_not_called()
        mock_ofa.deploy_kafka_producer.assert_not_called()
        mock_ofa.create_device_ksqldb_tables.assert_not_called()
        mock_ofa.deploy_device_supervisor.assert_not_called()
        mock_user_notify.success.assert_not_called()
