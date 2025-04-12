import unittest
from unittest.mock import patch, MagicMock
from openfactory.factories import deploy_apps_from_config_file


@patch("openfactory.factories.deploy_apps.get_apps_from_config_file")
@patch("openfactory.factories.deploy_apps.OpenFactoryManager")
@patch("openfactory.factories.deploy_apps.user_notify")
class TestDeployAppsFromConfigFile(unittest.TestCase):
    """
    Test deployment of apps based on a yaml_config_file
    """

    def test_deploy_apps_none(self, mock_notify, mock_manager_cls, mock_get_apps):
        """ Test case where yaml_config_file has no apps """
        # Simulate the case where no apps are returned (None)
        mock_get_apps.return_value = None

        deploy_apps_from_config_file("fake_config.yaml", ksqlClient=MagicMock())

        # Assert that `get_apps_from_config_file` was called with the right argument
        mock_get_apps.assert_called_once_with("fake_config.yaml")
        mock_manager_cls.assert_not_called()
        mock_notify.info.assert_not_called()

    def test_deploy_existing_application(self, mock_notify, mock_manager_cls, mock_get_apps):
        """ Test deployment of an already deployed app """
        # Simulate the case where an app already exists
        app_uuid = "1234-uuid"
        app_config = {"uuid": app_uuid}
        mock_get_apps.return_value = {"my_app": app_config}

        # Mock OpenFactoryManager to return the app_uuid in its list of deployed applications
        mock_manager = MagicMock()
        mock_manager.applications_uuid.return_value = [app_uuid]
        mock_manager_cls.return_value = mock_manager

        deploy_apps_from_config_file("fake_config.yaml", ksqlClient=MagicMock())

        # Assert that we informed about the app and that it was not redeployed
        mock_notify.info.assert_any_call("my_app:")
        mock_notify.info.assert_any_call(f"Application {app_uuid} exists already and was not deployed")
        mock_manager.deploy_

    def test_deploy_new_application(self, mock_notify, mock_manager_cls, mock_get_apps):
        """ Test deployment of a new app """
        # Simulate the case where a new app is deployed
        app_uuid = "5678-uuid"
        app_mock = {"uuid": app_uuid}
        mock_get_apps.return_value = {"new_app": app_mock}

        # Mock OpenFactoryManager to return an empty list of deployed applications (no app exists)
        mock_manager = MagicMock()
        mock_manager.applications_uuid.return_value = []
        mock_manager_cls.return_value = mock_manager

        deploy_apps_from_config_file("fake_config.yaml", ksqlClient=MagicMock())

        # Assert that the new app was deployed
        mock_notify.info.assert_any_call("new_app:")

        # Assert that deploy_openfactory_application was called with the correct app
        mock_manager.deploy_openfactory_application.assert_called_once_with(app_mock)
