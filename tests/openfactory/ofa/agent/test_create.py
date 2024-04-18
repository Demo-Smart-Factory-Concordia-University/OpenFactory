import os
from unittest import TestCase
from unittest.mock import patch
from click.testing import CliRunner

import openfactory.ofa as ofa
from openfactory.ofa.db import db
from openfactory.models.base import Base


@patch("openfactory.ofa.agent.create.create_agents_from_config_file")
class TestAgentCreate(TestCase):
    """
    Unit tests for ofa.agent.create
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

    def test_create(self, mock_create_agents_from_config_file):
        """
        Test create_agents_from_config_file called correctly
        """
        runner = CliRunner()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/mock_device.xml')
        result = runner.invoke(ofa.agent.click_create, [config_file])
        mock_create_agents_from_config_file.called_once_with(db.session, config_file, run=False, attach=False)
        self.assertEqual(result.exit_code, 0)

    def test_create_none_existent_file(self, mock_create_agents_from_config_file):
        """
        Test create_agents_from_config_file with none exisitng config file
        """
        runner = CliRunner()
        result = runner.invoke(ofa.agent.click_create, ['/does/not/exist/config_file.yml'])
        expect = ("Usage: create [OPTIONS] YAML_CONFIG_FILE\n"
                  "Try 'create --help' for help.\n"
                  "\n"
                  "Error: Invalid value for 'YAML_CONFIG_FILE': Path '/does/not/exist/config_file.yml' does not exist.\n")
        self.assertEqual(result.output, expect)
