import os
from unittest import TestCase
from unittest.mock import patch
from click.testing import CliRunner

import openfactory.ofa as ofa
from openfactory.ofa.db import db
from openfactory.models.base import Base


@patch("openfactory.factories.remove_devices_from_config_file")
class TestDeviceDown(TestCase):
    """
    Unit tests for ofa.stack.click_down
    """

    @classmethod
    def setUpClass(cls):
        """ Setup in memory sqlite db """
        db.conn_uri = 'sqlite:///:memory:'
        db.connect()
        Base.metadata.create_all(db.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(db.engine)
        db.session.close()

    def test_device_down(self, mock_remove_devices_from_config_file):
        """
        Test remove_devices_from_config_file called correctly
        """
        runner = CliRunner()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/mock_agents.yml')
        result = runner.invoke(ofa.device.click_down, [config_file])
        mock_remove_devices_from_config_file.called_once_with(db.session, config_file)
        self.assertEqual(result.exit_code, 0)

    def test_stack_down_none_existent_file(self, *args):
        """
        Test ofa.device.click_down with none exisitng config file
        """
        runner = CliRunner()
        result = runner.invoke(ofa.device.click_down, ['/does/not/exist/config_file.yml'])
        expect = ("Usage: down [OPTIONS] YAML_CONFIG_FILE\n"
                  "Try 'down --help' for help.\n"
                  "\n"
                  "Error: Invalid value for 'YAML_CONFIG_FILE': Path '/does/not/exist/config_file.yml' does not exist.\n")
        self.assertEqual(result.output, expect)
