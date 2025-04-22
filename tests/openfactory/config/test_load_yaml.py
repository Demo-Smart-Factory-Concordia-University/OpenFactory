import os
import unittest
from unittest.mock import patch, mock_open
from openfactory.config import load_yaml


class TestLoadYaml(unittest.TestCase):
    """
    Test cases for loading YAML files with environment variable substitution
    """

    @patch("openfactory.config.version", return_value="1.0.0")
    @patch("openfactory.config.load_dotenv")
    @patch("builtins.open", new_callable=mock_open, read_data="""
           key1: value1
           key2: ${ENV_VAR}
           """)
    def test_load_yaml_with_env_var(self, mock_open_file, mock_load_dotenv, mock_version):
        """ Test loading YAML with environment variable substitution """
        os.environ["ENV_VAR"] = "env_value"

        yaml_file = "dummy_path/openfactory.yml"
        result = load_yaml(yaml_file)

        self.assertEqual(result["key1"], "value1")
        self.assertEqual(result["key2"], "env_value")
        self.assertEqual(os.environ["OPENFACTORY_VERSION"], "v1.0.0")
        mock_load_dotenv.assert_called_once_with('.ofaenv')

        del os.environ["ENV_VAR"]

    @patch("openfactory.config.version", return_value="1.0.0")
    @patch("openfactory.config.load_dotenv")
    @patch("builtins.open", new_callable=mock_open, read_data="""
           key1: value1
           nested:
            child: null
           list:
            - item1
            - item2
           """)
    def test_load_yaml_without_env_var(self, mock_open_file, mock_load_dotenv, mock_version):
        """ Test loading YAML without environment variable substitution """
        yaml_file = "dummy_path/openfactory.yml"
        result = load_yaml(yaml_file)

        self.assertEqual(result["key1"], "value1")
        self.assertIsNone(result["nested"]["child"])
        self.assertEqual(result["list"], ["item1", "item2"])
        self.assertEqual(os.environ["OPENFACTORY_VERSION"], "v1.0.0")
        mock_load_dotenv.assert_called_once_with('.ofaenv')

    @patch("openfactory.config.version", return_value="1.0.0")
    @patch("openfactory.config.load_dotenv")
    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_load_yaml_file_not_found(self, mock_open_file, mock_load_dotenv, mock_version):
        """ Test loading YAML file that does not exist """
        yaml_file = "non_existent_file.yml"

        with self.assertRaises(FileNotFoundError):
            load_yaml(yaml_file)
