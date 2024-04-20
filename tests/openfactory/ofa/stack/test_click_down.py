import os
from unittest import TestCase
from unittest.mock import patch
from click.testing import CliRunner

import openfactory.ofa as ofa
from openfactory.ofa.db import db
from openfactory.models.base import Base


@patch("openfactory.ofa.stack.down.remove_infrastack")
class TestStackDown(TestCase):
    """
    Unit tests for ofa.stack.down
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

    def test_stack_down(self, mock_remove_infrastack):
        """
        Test remove_infrastack called correctly
        """
        runner = CliRunner()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/base_infra_mock.yml')
        result = runner.invoke(ofa.stack.click_down, [config_file])
        mock_remove_infrastack.called_once_with(db.session, config_file)
        self.assertEqual(result.exit_code, 0)

    def test_stack_down_none_existent_file(self, *args):
        """
        Test ofa.stack.click_down with none exisitng config file
        """
        runner = CliRunner()
        result = runner.invoke(ofa.stack.click_down, ['/does/not/exist/config_file.yml'])
        expect = ("Usage: down [OPTIONS] YAML_CONFIG_FILE\n"
                  "Try 'down --help' for help.\n"
                  "\n"
                  "Error: Invalid value for 'YAML_CONFIG_FILE': Path '/does/not/exist/config_file.yml' does not exist.\n")
        self.assertEqual(result.output, expect)
