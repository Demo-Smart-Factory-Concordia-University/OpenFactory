import os
import filecmp
from unittest import TestCase
from unittest.mock import patch, call, Mock, ANY
from sqlalchemy import select
from sqlalchemy.orm import Session
from paramiko.ssh_exception import SSHException

import tests.mocks as mock
from openfactory.exceptions import OFAException
from openfactory.ofa.db import db
from openfactory.models.user_notifications import user_notify
from openfactory.models.base import Base
from openfactory.models.nodes import Node
from openfactory.models.agents import Agent
from openfactory.models.containers import _docker_clients
from openfactory.factories import create_agents_from_config_file


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

    def setup_nodes(self, *args):
        """
        Setup a manager and a node
        """
        manager = Node(
            node_name='manager',
            node_ip='123.456.7.891',
            network='test-net'
        )
        db.session.add_all([manager])
        db.session.commit()
        node = Node(
            node_name='node1',
            node_ip='123.456.7.901'
        )
        db.session.add_all([node])
        db.session.commit()
        return manager, node

    def cleanup(self, *args):
        """
        Clean up all agents and nodes
        """
        # remove agents
        for agent in db.session.scalars(select(Agent)):
            db.session.delete(agent)
        # remove nodes
        for node in db.session.scalars(select(Node)):
            if node.node_name != 'manager':
                db.session.delete(node)
        # remove manager
        query = select(Node).where(Node.node_name == "manager")
        manager = db.session.execute(query).first()
        if manager:
            db.session.delete(manager[0])
        db.session.commit()

    @patch("openfactory.models.agents.Agent.create_container")
    def test_create_agents(self, mock_create_container, *args):
        """
        Test if agents are created correctly
        """
        manager, node = self.setup_nodes()

        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_agents.yml')
        create_agents_from_config_file(db.session, config_file)

        # check agents were created correctly
        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-001-AGENT")
        agent = db.session.execute(query).first()
        agent1 = agent[0]
        self.assertEqual(agent1.agent_port, 3001)
        self.assertEqual(agent1.node, manager)
        self.assertEqual(agent1.device_xml, 'mock_device.xml')
        self.assertEqual(agent1.cpus_reservation, 1.5)
        self.assertEqual(agent1.cpus_limit, 2.5)

        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-002-AGENT")
        agent = db.session.execute(query).first()
        agent2 = agent[0]
        self.assertEqual(agent2.agent_port, 3003)
        self.assertEqual(agent2.node, node)
        self.assertEqual(agent2.device_xml, 'mock_device.xml')
        self.assertEqual(agent2.cpus_reservation, 0.5)
        self.assertEqual(agent2.cpus_limit, 1.0)

        # check containers were created correctly
        args = mock_create_container.call_args_list
        self.assertEqual(mock_create_container.call_count, 2)
        self.assertTrue(call('adapter1.test.org', 7878, ANY, 1.5) in args)
        self.assertTrue(call('adapter2.test.org', 7879, ANY, 0) in args)

        # clean-up
        self.cleanup()

    @patch("openfactory.models.agents.Agent.create_container")
    @patch("openfactory.factories.agents.open_ofa")
    def test_create_agents_use_open_ofa(self, mock_open_ofa,  *args):
        """
        Test if create_agents_from_config_file uses open_ofa
        """
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mocks/mock_device.xml')
        mock_open_ofa.return_value = open(device_file, 'r')

        # create an agent using 'mock_device.xml' as device xml file
        self.setup_nodes()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_one_agent.yml')
        create_agents_from_config_file(db.session, config_file)

        # check it used 'open_ofa' to get the device file
        mock_open_ofa.assert_called_with(device_file)

        # clean-up
        self.cleanup()

    @patch("openfactory.models.agents.Agent.create_container")
    @patch("tempfile.TemporaryDirectory")
    def test_create_agents_xml_file(self, mock_tempdir, *args):
        """
        Test if agents are created with correct device xml file
        """
        # redirect TemporaryDirectory to a known folder
        tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mocks')
        mock_tempdir.return_value.__enter__.return_value = tmp_dir

        # create agents using 'mock_device.xml' as device xml file
        self.setup_nodes()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_agents.yml')
        create_agents_from_config_file(db.session, config_file)

        # check xml-file downloaded by 'create_agents_from_config_file' is correct
        xml_file = os.path.join(tmp_dir, 'device.xml')
        self.assertTrue(filecmp.cmp(xml_file,
                                    os.path.join(tmp_dir, 'mock_device.xml'),
                                    shallow=False))

        # clean-up
        self.cleanup()
        os.remove(xml_file)

    @patch("openfactory.models.agents.Agent.start")
    def test_create_agents_run(self, mock_start, *args):
        """
        Test if agents are started
        """
        self.setup_nodes()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_agents.yml')
        create_agents_from_config_file(db.session, config_file, run=True)

        # check containers were started
        self.assertEqual(mock_start.call_count, 2)

        # clean-up
        self.cleanup()

    @patch("openfactory.models.agents.Agent.attach")
    def test_create_agents_attach(self, mock_attach, *args):
        """
        Test if agents producers are created correctly
        """
        self.setup_nodes()

        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_agents.yml')
        create_agents_from_config_file(db.session, config_file, run=True, attach=True)

        # check containers were started
        args = mock_attach.call_args_list
        self.assertEqual(mock_attach.call_count, 2)
        self.assertTrue(call(1.0) in args)
        self.assertTrue(call(0) in args)

        # clean-up
        self.cleanup()

    def test_create_agents_missing_node(self, *args):
        """
        Test if OFAException raised when node is missing
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_agents.yml')

        # check OFAException raised
        self.assertRaises(OFAException, create_agents_from_config_file, db.session, config_file)

        # clean-up
        self.cleanup()

    def test_create_agents_agent_exist(self, *args):
        """
        Test if user_notify.info called if an agent already exists
        """
        self.setup_nodes()

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

    def test_create_agents_no_agent_device_file(self, *args):
        """
        Test if OFAException raised when agent device file is missing
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_agents_bug_device_file.yml')

        # check error raised
        self.assertRaises(OFAException, create_agents_from_config_file, db.session, config_file)

        # clean-up
        self.cleanup()

    def test_create_agents_ssh_error(self, mock_docker_apiclient, mock_DockerClient, *args):
        """
        Test if SSHException is handled
        """
        self.setup_nodes()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_agents.yml')

        # mock an SSHException
        _docker_clients.clear()
        mock_DockerClient.side_effect = SSHException('Mocking SSH connection error')

        # check SSHException is handled correctly
        create_agents_from_config_file(db.session, config_file, run=True, attach=True)
        calls = user_notify.fail.call_args_list
        self.assertIn(call('Could not create TEST-ZAIX-001-AGENT\nError was: Could not create container test-zaix-001-agent - Node is down'), calls)

        # check agent was not created
        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-001-AGENT")
        self.assertIsNone(db.session.execute(query).one_or_none())

        # clean-up
        mock_DockerClient.side_effect = None
        self.cleanup()

    def test_create_adapter(self, *args):
        """
        Test if adapter is created correctly
        """
        manager, node = self.setup_nodes()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_adapter.yml')
        create_agents_from_config_file(db.session, config_file)

        # check adapter configuration
        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-001-AGENT")
        agent = db.session.execute(query).one()
        adapter = agent[0].adapter_container
        self.assertEqual(adapter.node, manager)
        self.assertEqual(adapter.image, 'ofa/ofa_adapter')
        self.assertEqual(adapter.name, 'test-zaix-001-adapter')
        self.assertEqual(adapter.environment[0].variable, 'VAR1')
        self.assertEqual(adapter.environment[0].value, 'value1')
        self.assertEqual(adapter.environment[1].variable, 'VAR2')
        self.assertEqual(adapter.environment[1].value, 'value2')
        self.assertEqual(adapter.cpus, 2.5)

        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-002-AGENT")
        agent = db.session.execute(query).one()
        adapter = agent[0].adapter_container
        self.assertEqual(adapter.node, manager)
        self.assertEqual(adapter.image, 'ofa/ofa_adapter')
        self.assertEqual(adapter.name, 'test-zaix-002-adapter')
        self.assertEqual(adapter.environment[0].variable, 'VAR11')
        self.assertEqual(adapter.environment[0].value, 'value11')
        self.assertEqual(adapter.environment[1].variable, 'VAR12')
        self.assertEqual(adapter.environment[1].value, 'value12')
        self.assertEqual(adapter.cpus, 5)

        # clean-up
        self.cleanup()

    @patch("openfactory.models.containers.DockerContainer.start")
    def test_start_adapter(self, mock_container_start, *args):
        """
        Test if adapter is started
        """
        self.setup_nodes()
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
        self.setup_nodes()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_adapter.yml')
        create_agents_from_config_file(db.session, config_file)

        # check user_notify.success called
        args = user_notify.success.call_args_list
        self.assertTrue(call('Adapter test-zaix-001-adapter started successfully') in args)

        # clean-up
        self.cleanup()

    @patch("openfactory.models.agents.Agent.create_container")
    def test_adapter_ip(self, mock_create_container, *args):
        """
        Test adapter IP is set correctly when an adapter container is created
        """
        self.setup_nodes()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_adapter.yml')
        create_agents_from_config_file(db.session, config_file)

        # check adapter IP
        args = mock_create_container.call_args_list
        self.assertEqual(mock_create_container.call_count, 2)
        self.assertTrue(call('test-zaix-001-adapter', 7878, ANY, 1.5) in args)
        self.assertTrue(call('test-zaix-002-adapter', 7878, ANY, 0) in args)

        # clean-up
        self.cleanup()

    @patch("openfactory.models.agents.Agent.create_adapter")
    def test_adapter_create_error(self, mock_create_adapter, *args):
        """
        Test if adapter create error handled
        """
        mock_create_adapter.side_effect = OFAException('Mock error')
        self.setup_nodes()
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_adapter.yml')
        create_agents_from_config_file(db.session, config_file)

        # check adapter IP
        args = user_notify.fail.call_args_list
        self.assertTrue(call('Could not create test-zaix-001-adapter\nError was: Mock error') in args)

        # clean-up
        mock_create_adapter.side_effect = None
        self.cleanup()
