import unittest
from unittest.mock import patch, MagicMock
import signal
import os
from openfactory.apps import OpenFactoryApp


class TestOpenFactoryApp(unittest.TestCase):
    """
    Tests for class OpenFactoryApp
    """

    def setUp(self):
        self.ksql_mock = MagicMock()

        # Patch AssetProducer
        self.asset_producer_patcher = patch("openfactory.assets.asset_base.AssetProducer")
        self.MockAssetProducer = self.asset_producer_patcher.start()
        self.addCleanup(self.asset_producer_patcher.stop)

        # Patch add_attribute
        self.add_attribute_patcher = patch.object(OpenFactoryApp, 'add_attribute')
        self.mock_add_attribute = self.add_attribute_patcher.start()
        self.addCleanup(self.add_attribute_patcher.stop)

        # Patch deregister_asset
        self.deregister_patcher = patch('openfactory.apps.ofaapp.deregister_asset')
        self.mock_deregister = self.deregister_patcher.start()
        self.addCleanup(self.deregister_patcher.stop)

    def test_inheritance(self):
        """ Test if OpenFactoryApp derives from Asset """
        from openfactory.assets import Asset
        self.assertTrue(issubclass(OpenFactoryApp, Asset), "OpenFactoryApp should derive from Asset")

    def test_initialization_with_env_vars(self):
        """ Test initialization with external environment variables set """
        with patch.dict(os.environ, {
            'APPLICATION_VERSION': '1.0.0',
            'APPLICATION_MANUFACTURER': 'TestFactory',
            'APPLICATION_LICENSE': 'MIT',
            'APP_UUID': 'env-uuid'
        }, clear=True):
            import importlib
            import openfactory.apps.ofaapp as openfactoryapp
            importlib.reload(openfactoryapp)
            OpenFactoryApp = openfactoryapp.OpenFactoryApp

            with patch.object(OpenFactoryApp, 'add_attribute'), patch('openfactory.utils.assets.deregister_asset'):

                app = OpenFactoryApp(app_uuid='init-uuid', ksqlClient=self.ksql_mock)

                self.assertEqual(app.APPLICATION_VERSION, '1.0.0')
                self.assertEqual(app.APPLICATION_MANUFACTURER, 'TestFactory')
                self.assertEqual(app.APPLICATION_LICENSE, 'MIT')
                self.assertEqual(app.asset_uuid, 'env-uuid')

    def test_initialization_with_defaults(self):
        """ Test initialization with no external environment variables set """
        app = OpenFactoryApp(app_uuid='init-uuid', ksqlClient=self.ksql_mock, bootstrap_servers='mock_bootstrap')

        self.assertEqual(app.APPLICATION_VERSION, 'latest')
        self.assertEqual(app.APPLICATION_MANUFACTURER, 'OpenFactory')
        self.assertEqual(app.APPLICATION_LICENSE, 'BSD-3-Clause license')
        self.assertEqual(app.asset_uuid, 'init-uuid')

    def test_attributes_added(self):
        """ Test if attributes are added correctly to the app """
        app = OpenFactoryApp(app_uuid='init-uuid', ksqlClient=self.ksql_mock, bootstrap_servers='mock_bootstrap')

        # Get the list of add_attribute calls.
        calls = app.add_attribute.call_args_list

        # Check that the expected attribute_ids are present.
        expected_ids = ['application_version', 'application_manufacturer', 'application_license']
        actual_ids = [call_obj.kwargs['attribute_id'] for call_obj in calls]
        for attr in expected_ids:
            self.assertIn(attr, actual_ids, f"{attr} not found in add_attribute calls.")

        # For each attribute, check that the asset_attribute was built with the correct parameters
        for call_obj in calls:
            attr_id = call_obj.kwargs['attribute_id']
            asset_attr = call_obj.kwargs['asset_attribute']

            # Check values and tags based on attribute_id.
            if attr_id == 'application_version':
                self.assertEqual(asset_attr.value, 'latest', "Value mismatch for application_version")
                self.assertEqual(asset_attr.type, 'Events', f"Type mismatch for {attr_id}")
                self.assertEqual(asset_attr.tag, 'Application.Version', "Tag mismatch for application_version")
            elif attr_id == 'application_manufacturer':
                self.assertEqual(asset_attr.value, 'OpenFactory', "Value mismatch for application_manufacturer")
                self.assertEqual(asset_attr.type, 'Events', f"Type mismatch for {attr_id}")
                self.assertEqual(asset_attr.tag, 'Application.Manufacturer', "Tag mismatch for application_manufacturer")
            elif attr_id == 'application_license':
                self.assertEqual(asset_attr.value, 'BSD-3-Clause license', "Value mismatch for application_license")
                self.assertEqual(asset_attr.type, 'Events', f"Type mismatch for {attr_id}")
                self.assertEqual(asset_attr.tag, 'Application.License', "Tag mismatch for application_license")
            else:
                self.fail(f"Unexpected attribute_id: {attr_id}")

    @patch('openfactory.apps.ofaapp.configure_prefixed_logger')
    def test_logger_is_configured_correctly(self, mock_configure_logger):
        """ Test that logger is configured with correct prefix and level. """
        mock_logger = MagicMock()
        mock_configure_logger.return_value = mock_logger

        app = OpenFactoryApp(
            app_uuid='test-uuid',
            ksqlClient=self.ksql_mock,
            bootstrap_servers='mock-bootstrap',
            loglevel='DEBUG'
        )

        mock_configure_logger.assert_called_once_with(
            'test-uuid',
            prefix='TEST-UUID',
            level='DEBUG'
        )
        self.assertIs(app.logger, mock_logger)
        mock_logger.info.assert_called_with("Setup OpenFactory App test-uuid")

    def test_signal_sigint(self):
        """ Test signal SIGINT """
        app = OpenFactoryApp(app_uuid='init-uuid', ksqlClient=self.ksql_mock, bootstrap_servers='mock_bootstrap')
        app.app_event_loop_stopped = MagicMock()

        with patch('openfactory.apps.ofaapp.signal.Signals') as mock_signals:
            mock_signals.return_value.name = 'SIGINT'
            # Assert that SystemExit is raised
            with self.assertRaises(SystemExit):
                app.signal_handler(signal.SIGINT, None)

        # Check that deregister_asset was called with the expected arguments
        self.mock_deregister.assert_called_once_with(
            'init-uuid', ksqlClient=self.ksql_mock, bootstrap_servers='mock_bootstrap'
        )
        # Check app_event_loop_stopped was called
        app.app_event_loop_stopped.assert_called_once()

    def test_signal_sigterm(self):
        """ Test signal SIGTERM """
        app = OpenFactoryApp(app_uuid='init-uuid', ksqlClient=self.ksql_mock, bootstrap_servers='mock_bootstrap')
        app.app_event_loop_stopped = MagicMock()

        with patch('openfactory.apps.ofaapp.signal.Signals') as mock_signals:
            mock_signals.return_value.name = 'SIGTERM'
            # Assert that SystemExit is raised
            with self.assertRaises(SystemExit):
                app.signal_handler(signal.SIGINT, None)

        # Check that deregister_asset was called with the expected arguments
        self.mock_deregister.assert_called_once_with(
            'init-uuid', ksqlClient=self.ksql_mock, bootstrap_servers='mock_bootstrap'
        )
        # Check app_event_loop_stopped was called
        app.app_event_loop_stopped.assert_called_once()

    def test_main_loop_not_implemented(self):
        """ Test call to main_loop raise NotImplementedError """
        app = OpenFactoryApp(app_uuid='init-uuid', ksqlClient=self.ksql_mock, bootstrap_servers='mock_bootstrap')
        with self.assertRaises(NotImplementedError):
            app.main_loop()

    def test_run_invokes_main_loop(self):
        """ Test run method invokes main_loop """
        app = OpenFactoryApp(app_uuid='init-uuid', ksqlClient=self.ksql_mock, bootstrap_servers='mock_bootstrap')
        app.main_loop = MagicMock()
        app.run()
        app.main_loop.assert_called_once()

    def test_run_handles_main_loop_exception(self):
        """ Test handling of exception in main_loop """
        app = OpenFactoryApp(
            app_uuid='init-uuid',
            ksqlClient=self.ksql_mock,
            bootstrap_servers='mock_bootstrap'
        )
        app.main_loop = MagicMock(side_effect=Exception("Boom"))

        with patch.object(app.logger, 'exception') as mock_logger_exception:
            app.run()
            mock_logger_exception.assert_called_once()
            args, kwargs = mock_logger_exception.call_args
            assert "An error occurred in the main_loop of the app." in args[0]
            self.mock_deregister.assert_called_once()
