import os
from unittest import TestCase
from unittest.mock import patch, call, Mock
from sqlalchemy import select
from sqlalchemy.orm import Session

import tests.mocks as mock
from openfactory.exceptions import OFAException
from openfactory.ofa.db import db
from openfactory.docker.docker_access_layer import dal
from openfactory.models.user_notifications import user_notify
from openfactory.models.base import Base
from openfactory.models.agents import Agent
from openfactory.factories import create_agents_from_config_file


@patch.object(Agent, 'status', new_callable=Mock(return_value='running'))
@patch("openfactory.models.agents.AgentKafkaProducer", return_value=mock.agent_kafka_producer)
@patch("docker.DockerClient", return_value=mock.docker_client)
@patch("docker.APIClient", return_value=mock.docker_apiclient)
class Test_create_agents_from_config_file(TestCase):
    """
    Unit test of create_agents_from_config_file factory
    """

    @classmethod
    def setUpClass(cls):
        """ Setup in memory sqlite db """
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
        """ Start a new session """
        db.session = Session(db.engine)

        """ Reset mocks """
        mock.docker_client.reset_mock()
        mock.docker_container.reset_mock()
        mock.docker_images.reset_mock()
        user_notify.success.reset_mock()
        user_notify.fail.reset_mock()
        user_notify.info.reset_mock()

    def tearDown(self):
        """ Rollback all transactions """
        db.session.rollback()

    def cleanup(self, *args):
        """
        Clean up all agents
        """
        # remove agents
        for agent in db.session.scalars(select(Agent)):
            db.session.delete(agent)

        db.session.commit()

    def test_create_agents(self, *args):
        """
        Test if agents are created correctly
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_agents.yml')
        create_agents_from_config_file(db.session, config_file)

        # check agents were created correctly
        xml_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'mocks/mock_device.xml')
        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-001-AGENT")
        agent = db.session.execute(query).first()
        agent1 = agent[0]
        self.assertEqual(agent1.agent_port, 3001)
        self.assertEqual(agent1.device_xml, xml_file)
        self.assertEqual(agent1.cpus_reservation, 1.5)
        self.assertEqual(agent1.cpus_limit, 2.5)

        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-002-AGENT")
        agent = db.session.execute(query).first()
        agent2 = agent[0]
        self.assertEqual(agent2.agent_port, 3003)
        self.assertEqual(agent2.device_xml, xml_file)
        self.assertEqual(agent2.cpus_reservation, 0.5)
        self.assertEqual(agent2.cpus_limit, 1.0)

        # clean-up
        self.cleanup()

    @patch("openfactory.models.agents.Agent.start")
    def test_create_agents_run(self, mock_start, *args):
        """
        Test if agents are started
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_agents.yml')
        create_agents_from_config_file(db.session, config_file, run=True)

        # check services were started
        self.assertEqual(mock_start.call_count, 2)

        # clean-up
        self.cleanup()

    @patch("openfactory.models.agents.Agent.start")
    @patch("openfactory.models.agents.Agent.attach")
    def test_create_agents_attach(self, mock_attach, *args):
        """
        Test if agents producers services are started
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_agents.yml')
        create_agents_from_config_file(db.session, config_file, run=False, attach=True)

        # check producer services were started
        self.assertEqual(mock_attach.call_count, 2)

        # clean-up
        self.cleanup()

    def test_create_agents_agent_exist(self, *args):
        """
        Test if user_notify.info called if an agent already exists
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_agents.yml')
        create_agents_from_config_file(db.session, config_file)

        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_one_agent.yml')
        create_agents_from_config_file(db.session, config_file)

        # check user_notify.info called
        args = user_notify.info.call_args_list
        self.assertTrue(call('Agent TEST-ZAIX-001-AGENT exists already and was not created') in args)

        # clean-up
        self.cleanup()

    def test_create_adapter(self, *args):
        """
        Test if adapter is created correctly
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_adapter.yml')
        create_agents_from_config_file(db.session, config_file)

        # check adapter configuration
        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-001-AGENT")
        agent = db.session.execute(query).one()
        adapter = agent[0].adapter_container
        self.assertEqual(adapter.image, 'ofa/ofa_adapter')
        self.assertEqual(adapter.name, 'test-zaix-001-adapter')
        self.assertEqual(adapter.environment[0].variable, 'VAR1')
        self.assertEqual(adapter.environment[0].value, 'value1')
        self.assertEqual(adapter.environment[1].variable, 'VAR2')
        self.assertEqual(adapter.environment[1].value, 'value2')

        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-002-AGENT")
        agent = db.session.execute(query).one()
        adapter = agent[0].adapter_container
        self.assertEqual(adapter.image, 'ofa/ofa_adapter')
        self.assertEqual(adapter.name, 'test-zaix-002-adapter')
        self.assertEqual(adapter.environment[0].variable, 'VAR11')
        self.assertEqual(adapter.environment[0].value, 'value11')
        self.assertEqual(adapter.environment[1].variable, 'VAR12')
        self.assertEqual(adapter.environment[1].value, 'value12')

        # clean-up
        self.cleanup()

    @patch("openfactory.models.containers.DockerContainer.start")
    def test_start_adapter(self, mock_container_start, *args):
        """
        Test if adapter is started
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_adapter.yml')
        create_agents_from_config_file(db.session, config_file)

        # check adapters started
        self.assertEqual(mock_container_start.call_count, 2)

        # clean-up
        self.cleanup()

    def test_adapter_user_notifications(self, *args):
        """
        Test user notifications for adapter
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_adapter.yml')
        create_agents_from_config_file(db.session, config_file)

        # check user_notify.success called
        args = user_notify.success.call_args_list
        self.assertTrue(call('Adapter test-zaix-001-adapter started successfully') in args)

        # clean-up
        self.cleanup()

    @patch("openfactory.models.agents.Agent.create_adapter")
    def test_adapter_create_error(self, mock_create_adapter, *args):
        """
        Test if adapter create error handled
        """
        mock_create_adapter.side_effect = OFAException('Mock error')
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_adapter.yml')
        create_agents_from_config_file(db.session, config_file)

        # check adapter IP
        args = user_notify.fail.call_args_list
        self.assertTrue(call('Could not create test-zaix-001-adapter\nError was: Mock error') in args)

        # clean-up
        mock_create_adapter.side_effect = None
        self.cleanup()
