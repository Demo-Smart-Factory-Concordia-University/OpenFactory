import os
from unittest import TestCase
from unittest.mock import patch
from click.testing import CliRunner

import openfactory.ofa as ofa
from openfactory.ofa.db import db
from openfactory.models.base import Base


@patch("openfactory.ofa.stack.up.create_infrastack")
class TestStackUp(TestCase):
    """
    Unit tests for ofa.stack.up
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

    def test_stack_up(self, mock_create_infrastack):
        """
        Test create_infrastack called correctly
        """
        runner = CliRunner()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/base_infra_mock.yml')
        result = runner.invoke(ofa.stack.click_up, [config_file])
        mock_create_infrastack.called_once_with(db.session, config_file)
        self.assertEqual(result.exit_code, 0)

    def test_stack_up_none_existent_file(self, mock_create_infrastack):
        """
        Test ofa.stack.click_up with none exisitng config file
        """
        runner = CliRunner()
        result = runner.invoke(ofa.stack.click_up, ['/does/not/exist/config_file.yml'])
        expect = ("Usage: up [OPTIONS] YAML_CONFIG_FILE\n"
                  "Try 'up --help' for help.\n"
                  "\n"
                  "Error: Invalid value for 'YAML_CONFIG_FILE': Path '/does/not/exist/config_file.yml' does not exist.\n")
        self.assertEqual(result.output, expect)
