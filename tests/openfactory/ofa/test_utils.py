import unittest
from unittest.mock import patch, MagicMock
from openfactory.ofa.utils import process_yaml_files


class TestProcessYamlFiles(unittest.TestCase):
    """
    Test the process_yaml_files function
    """

    @patch('openfactory.ofa.utils.find_yaml_files')
    @patch('openfactory.ofa.utils.os.path.isdir')
    @patch('openfactory.ofa.utils.os.path.isfile')
    @patch('openfactory.ofa.utils.user_notify')
    def test_process_yaml_files_folder(self, mock_notify, mock_isfile, mock_isdir, mock_find_yaml_files):
        """ Test the process_yaml_files function with a folder containing YAML files """
        # Setup the mocks
        mock_isdir.return_value = True  # Simulate directory being present
        mock_isfile.return_value = False  # Simulate not being a file
        mock_find_yaml_files.return_value = ['app_mock1.yml', 'app_mock2.yml']  # Mock the list of YAML files

        # Mock the action function
        mock_action_func = MagicMock()

        # Run the function
        process_yaml_files('mock_folder', dry_run=False,
                           action_func=mock_action_func,
                           action_name="deployed",
                           pattern='app_*.yml')

        # Assert the find_yaml_files was called
        mock_find_yaml_files.assert_called_with('mock_folder', pattern='app_*.yml')

        # Check deployment calls
        mock_action_func.assert_any_call('app_mock1.yml')
        mock_action_func.assert_any_call('app_mock2.yml')

        # Check notification for deploying
        mock_notify.info.assert_any_call("[INFO] Deployed from 'app_mock1.yml' ...")
        mock_notify.info.assert_any_call("[INFO] Deployed from 'app_mock2.yml' ...")

    @patch('openfactory.ofa.utils.find_yaml_files')
    @patch('openfactory.ofa.utils.os.path.isdir')
    @patch('openfactory.ofa.utils.os.path.isfile')
    @patch('openfactory.ofa.utils.user_notify')
    def test_process_yaml_files_folder_dry_run(self, mock_notify, mock_isfile, mock_isdir, mock_find_yaml_files):
        """ Test the process_yaml_files function with a folder containing YAML files on dry-run """
        # Setup the mocks
        mock_isdir.return_value = True
        mock_isfile.return_value = False
        mock_find_yaml_files.return_value = ['dev_mock1.yml', 'dev_mock2.yml']

        # Mock the action function
        mock_action_func = MagicMock()

        # Run the function
        process_yaml_files('mock_folder', dry_run=True,
                           action_func=mock_action_func,
                           action_name="deployed",
                           pattern='dev_*.yml')

        # Assert the find_yaml_files was called
        mock_find_yaml_files.assert_called_with('mock_folder', pattern='dev_*.yml')

        # Check dry-run notifications
        mock_notify.info.assert_any_call("[DRY-RUN] dev_mock1.yml would be deployed.")
        mock_notify.info.assert_any_call("[DRY-RUN] dev_mock2.yml would be deployed.")

        # Ensure the action function was not called
        mock_action_func.assert_not_called()

    @patch('openfactory.ofa.utils.os.path.isfile')
    def test_process_yaml_files_file(self, mock_isfile):
        """ Test the process_yaml_files function with a single YAML file """
        # Setup the mocks
        mock_isfile.return_value = True

        # Mock the action function
        mock_action_func = MagicMock()

        # Run the function
        process_yaml_files('mock_file.yml', dry_run=False, action_func=mock_action_func, action_name="deployed")

        # Check that the action function was called with the correct file
        mock_action_func.assert_called_with('mock_file.yml')

    @patch('openfactory.ofa.utils.find_yaml_files')
    @patch('openfactory.ofa.utils.os.path.isdir')
    @patch('openfactory.ofa.utils.os.path.isfile')
    @patch('openfactory.ofa.utils.user_notify')
    def test_process_yaml_files_no_files_found(self, mock_notify, mock_isfile, mock_isdir, mock_find_yaml_files):
        """ Test the process_yaml_files function when no YAML files are found """
        # Setup the mocks
        mock_isdir.return_value = True  # Simulate directory being present
        mock_isfile.return_value = False  # Simulate not being a file
        mock_find_yaml_files.return_value = []  # No YAML files found

        # Run the function
        process_yaml_files('mock_folder', dry_run=False, action_func=MagicMock(), action_name="deployed")

        # Check that failure notification is triggered
        mock_notify.fail.assert_called_with("No YAML files found in 'mock_folder'.")

    @patch('openfactory.ofa.utils.os.path.isfile')
    @patch('openfactory.ofa.utils.user_notify')
    def test_process_yaml_files_dry_run_file(self, mock_notify, mock_isfile):
        """ Test the process_yaml_files function with a single file in dry-run mode """
        # Setup the mocks
        mock_isfile.return_value = True

        # Mock the action function
        mock_action_func = MagicMock()

        # Run the function
        process_yaml_files('mock_file.yml', dry_run=True, action_func=mock_action_func, action_name="processed")

        # Check dry-run notification
        mock_notify.info.assert_called_with("[DRY-RUN] mock_file.yml would be processed.")

        # Ensure the action function was not called
        mock_action_func.assert_not_called()
