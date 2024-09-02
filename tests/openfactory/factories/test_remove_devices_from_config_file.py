import os
import docker
from unittest import TestCase
from unittest.mock import patch, Mock, call
import docker.errors
from sqlalchemy import select

import tests.mocks as mock
from openfactory.ofa.db import db
from openfactory.docker.docker_access_layer import dal
from openfactory.factories import create_agents_from_config_file
from openfactory.factories import remove_devices_from_config_file
from openfactory.models.user_notifications import user_notify
from openfactory.models.base import Base
from openfactory.models.agents import Agent
from openfactory.exceptions import OFAException


@patch.object(Agent, 'status', new_callable=Mock(return_value='running'))
@patch("openfactory.models.agents.AgentKafkaProducer", return_value=mock.agent_kafka_producer)
@patch("docker.DockerClient", return_value=mock.docker_client)
@patch("docker.APIClient", return_value=mock.docker_apiclient)
class Test_remove_devices_from_config_file(TestCase):
    """
    Unit tests for remove_agents_from_config_file
    """

    @classmethod
    def setUpClass(cls):
        """ setup in memory sqlite db """
        print("Setting up in memory sqlite db")
        db.conn_uri = 'sqlite:///:memory:'
        db.connect()
        Base.metadata.create_all(db.engine)
        user_notify.setup(success_msg=Mock(),
                          fail_msg=Mock(),
                          info_msg=Mock())
        dal.docker_client = mock.docker_client

    @classmethod
    def tearDownClass(cls):
        print("\nTear down in memory sqlite db")
        Base.metadata.drop_all(db.engine)
        db.session.close()

    @classmethod
    def setUp(self):
        """ Reset mocks """
        user_notify.success.reset_mock()
        user_notify.info.reset_mock()
        user_notify.fail.reset_mock()

    @classmethod
    def tearDown(self):
        """ rollback all transactions """
        db.session.rollback()

    def cleanup(self, *args):
        """
        Clean up all stacks and nodes
        """
        # remove agents
        for agent in db.session.scalars(select(Agent)):
            db.session.delete(agent)
        db.session.commit()

    def test_remove_devices(self, *args):
        """
        Test tear down of devices
        """
        # setup agents
        config_agent = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'mocks/mock_agents.yml')
        create_agents_from_config_file(db.session, config_agent)

        # remove agent
        config_agent = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'mocks/mock_one_agent.yml')
        remove_devices_from_config_file(db.session, config_agent)

        # check agent-001 was removed but not agent-002
        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-001-AGENT")
        self.assertEqual(db.session.execute(query).one_or_none(), None)
        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-002-AGENT")
        self.assertEqual(db.session.execute(query).one_or_none() is None, False)

        # remove agent-001 and agent-002
        config_agent = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'mocks/mock_agents.yml')
        remove_devices_from_config_file(db.session, config_agent)

        # check agent-002 removed
        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-002-AGENT")
        self.assertEqual(db.session.execute(query).one_or_none(), None)

        # clean up
        self.cleanup()

    def test_remove_devices_notifications(self, *args):
        """
        Test user notifications during device removal
        """

        # setup agent
        config_agent = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'mocks/mock_one_agent.yml')
        create_agents_from_config_file(db.session, config_agent)

        # remove agent
        user_notify.info.reset_mock()
        user_notify.success.reset_mock()
        config_agent = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'mocks/mock_agents.yml')
        remove_devices_from_config_file(db.session, config_agent)

        # check notifications
        calls = user_notify.info.call_args_list
        self.assertEqual(calls[0], call('zaix-001:'))
        self.assertEqual(calls[1], call('zaix-003:'))
        self.assertEqual(calls[2], call('No Agent TEST-ZAIX-002-AGENT defined in OpenFactory'))

        calls = user_notify.success.call_args_list
        self.assertIn(call('Kafka producer for agent TEST-ZAIX-001-AGENT stopped successfully'), calls)
        self.assertIn(call('Agent TEST-ZAIX-001-AGENT stopped successfully'), calls)
        self.assertIn(call('Agent TEST-ZAIX-001-AGENT removed successfully'), calls)
        self.assertIn(call('TEST-ZAIX-001 removed successfully'), calls)

        # clean up
        self.cleanup()

    def test_remove_devices_capture_OFAException(self, *args):
        """
        Test OFAException is handled during device removal
        """
        # setup agent
        config_agent = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'mocks/mock_one_agent.yml')

        # make db_session.execute(query).one_or_none() to return mocked agent instances
        mock_agent_instance = Mock()
        mock_db_session = Mock()
        mock_db_session.execute.return_value.one_or_none.return_value = [mock_agent_instance]

        # make delete agent to raise OFAException
        mock_db_session.delete = Mock(side_effect=OFAException('Delete error'))
        remove_devices_from_config_file(mock_db_session, config_agent)

        # check errors were captured and handled
        calls = user_notify.fail.call_args_list
        self.assertIn(call('Cannot remove TEST-ZAIX-001 - Delete error'), calls)

        # clean up
        self.cleanup()

    def test_remove_devices_docker_api_error(self, *args):
        """
        Test Docker API error is handled during device removal
        """
        # setup agent
        config_agent = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'mocks/mock_one_agent.yml')
        create_agents_from_config_file(db.session, config_agent)

        # mock a Docker API error
        mock.docker_service.remove.side_effect = docker.errors.APIError('Mocking Docker API error')

        # check it is handled correctly
        remove_devices_from_config_file(db.session, config_agent)
        calls = user_notify.fail.call_args_list
        self.assertIn(call('Cannot remove TEST-ZAIX-001 - Mocking Docker API error'), calls)

        # clean up
        mock.docker_service.remove.side_effect = None
        self.cleanup()
