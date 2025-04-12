import unittest
from unittest.mock import MagicMock, patch
from openfactory.assets import AssetAttribute
from openfactory.apps.supervisor import BaseSupervisor


class TestSupervisor(BaseSupervisor):
    """ A testable subclass of BaseSupervisor with mocked abstract methods """

    def available_commands(self):
        return [
            {"command": "start", "description": "Start the device"},
            {"command": "stop", "description": "Stop the device"}
        ]

    def on_command(self, msg_key, msg_value):
        """ Mocked method """
        pass


class BaseSupervisorTestCase(unittest.TestCase):
    """
    Tests for class BaseSupervisor
    """

    def setUp(self):
        self.ksql_mock = MagicMock()

        # Patch AssetProducer
        self.asset_producer_patcher = patch("openfactory.assets.asset_class.AssetProducer")
        self.MockAssetProducer = self.asset_producer_patcher.start()
        self.addCleanup(self.asset_producer_patcher.stop)

        # Patch add_attribute
        self.add_attribute_patcher = patch.object(BaseSupervisor, 'add_attribute')
        self.mock_add_attribute = self.add_attribute_patcher.start()
        self.addCleanup(self.add_attribute_patcher.stop)

    def test_inheritance(self):
        """ Test if OpenFactoryApp derives from Asset """
        from openfactory.apps import OpenFactoryApp
        self.assertTrue(issubclass(BaseSupervisor, OpenFactoryApp),
                        "BaseSupervisor should derive from OpenFactoryApp")

    def test_constructor_adds_device_attribute(self):
        """ Test if supervisor attributes are set """
        TestSupervisor("sup-123", "dev-456", self.ksql_mock, bootstrap_servers='mock_bootstrap_servers')

        self.mock_add_attribute.assert_any_call(
            attribute_id='device_added',
            asset_attribute=AssetAttribute(value='dev-456', type='Events', tag='DeviceAdded')
        )

    @patch('openfactory.apps.supervisor.base_supervisor.Asset')
    def test_send_available_commands(self, MockAsset):
        """ Test _send_available_commands method """
        # Setup
        mock_asset_instance = MockAsset.return_value
        supervisor = TestSupervisor("sup-123", "dev-456", self.ksql_mock, bootstrap_servers='mock_bootstrap_servers')

        # Execute
        supervisor._send_available_commands()

        # Collect call arguments
        calls = mock_asset_instance.add_attribute.call_args_list

        # Check that the expected attribute_ids are present
        expected_ids = ['start', 'stop']
        actual_ids = [call_obj.kwargs['attribute_id'] for call_obj in calls]
        for attr_id in expected_ids:
            self.assertIn(attr_id, actual_ids, f"{attr_id} not found in add_attribute calls.")

        # Check content of asset_attribute per attribute_id
        for call_obj in calls:
            attr_id = call_obj.kwargs['attribute_id']
            asset_attr = call_obj.kwargs['asset_attribute']

            if attr_id == 'start':
                self.assertEqual(asset_attr.value, 'Start the device')
                self.assertEqual(asset_attr.type, 'Method')
                self.assertEqual(asset_attr.tag, 'Method')
            elif attr_id == 'stop':
                self.assertEqual(asset_attr.value, 'Stop the device')
                self.assertEqual(asset_attr.type, 'Method')
                self.assertEqual(asset_attr.tag, 'Method')
            else:
                self.fail(f"Unexpected attribute_id: {attr_id}")

    @patch('openfactory.apps.supervisor.base_supervisor.KafkaCommandsConsumer')
    @patch.object(TestSupervisor, '_send_available_commands')
    def test_main_loop_calls_consume(self, mock_send_commands, MockKafkaConsumer):
        """ Test command consumer in main loop """
        # Setup
        mock_consumer_instance = MockKafkaConsumer.return_value
        supervisor = TestSupervisor("sup-123", "dev-456", self.ksql_mock, bootstrap_servers='mock_bootstrap_servers')

        # Execute
        supervisor.main_loop()

        # Assert
        mock_send_commands.assert_called_once()
        MockKafkaConsumer.assert_called_once_with(
            consumer_group_id='sup-123-SUPERVISOR-GROUP',
            asset_uuid='dev-456',
            on_command=supervisor.on_command,
            ksqlClient=self.ksql_mock,
            bootstrap_servers='mock_bootstrap_servers'
        )
        mock_consumer_instance.consume.assert_called_once()

    def test_available_commands_not_implemented(self):
        """ Test call to available_commands raise NotImplementedError """
        sup = BaseSupervisor('sup-uuid', "dev-uuid", ksqlClient=self.ksql_mock, bootstrap_servers='mock_bootstrap')
        with self.assertRaises(NotImplementedError):
            sup.available_commands()

    def test_on_command_not_implemented(self):
        """ Test call to on_command raise NotImplementedError """
        sup = BaseSupervisor('sup-uuid', "dev-uuid", ksqlClient=self.ksql_mock, bootstrap_servers='mock_bootstrap')
        with self.assertRaises(NotImplementedError):
            sup.on_command("msg_key", "msg_value")
