import os
from unittest import TestCase
from unittest.mock import patch, call
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import openfactory.config as config
from openfactory.models.base import Base
from openfactory.models.nodes import Node
from openfactory.models.agents import Agent
import tests.mocks as mock


@patch("docker.DockerClient", return_value=mock.docker_client)
class TestAgent(TestCase):
    """
    Unit tests for Agent model
    """

    @classmethod
    def setUpClass(cls):
        """ setup in memory sqlite db """
        print("Setting up in memory sqlite db")
        cls.db_engine = create_engine('sqlite:///:memory:')
        Base.metadata.drop_all(cls.db_engine)
        Base.metadata.create_all(cls.db_engine)

    @classmethod
    def tearDownClass(cls):
        print("\nTear down in memory sqlite db")
        Base.metadata.drop_all(cls.db_engine)

    @classmethod
    def setUp(self):
        """ Start a new session """
        self.session = Session(self.db_engine)

    def test_class_parent(self, *args):
        """
        Test parent of class is Base
        """
        self.assertEqual(Agent.__bases__[0], Base)

    def test_table_name(self, *args):
        """
        Test table name
        """
        self.assertEqual(Agent.__tablename__, 'mtc_agents')

    def test_agent_setup(self, *args):
        """
        Test setup and tear down of an Agent
        """
        agent = Agent(uuid='test-agent',
                      agent_port=5000)
        self.session.add_all([agent])
        self.session.commit()

        query = select(Agent).where(Agent.uuid == "test-agent")
        agent = self.session.execute(query).first()
        self.assertEqual(agent[0].uuid, 'test-agent')
        self.assertEqual(agent[0].agent_port, 5000)
        self.assertEqual(agent[0].external, False)

        # clean-up
        self.session.delete(agent[0])
        self.session.commit()

    def test_agent_uuid_unique(self, *args):
        """
        Test Agent.uuid is required to be unique
        """
        agent1 = Agent(uuid='test-agent',
                       agent_port=5000)
        agent2 = Agent(uuid='test-agent',
                       agent_port=6000)
        self.session.add_all([agent1, agent2])
        self.assertRaises(IntegrityError, self.session.commit)

    def test_agent_url(self, *args):
        """
        Test hybride property 'agent_url' of an Agent
        """
        agent = Agent(uuid='test-agent',
                      agent_port=5000)
        node = Node(
            node_name='manager',
            node_ip='123.456.7.891',
            network='test-net'
        )
        agent.node = node
        self.session.add_all([node, agent])
        self.session.commit()

        self.assertEqual(agent.agent_url, '123.456.7.891')

        # clean-up
        self.session.delete(agent)
        self.session.delete(node)
        self.session.commit()

    def test_device_uuid(self, *args):
        """
        Test hybride property 'device_uuid' of an Agent
        """
        agent = Agent(uuid='test-agent',
                      agent_port=5000)
        self.session.add_all([agent])
        self.session.commit()

        self.assertEqual(agent.device_uuid, 'TEST')

        # clean-up
        self.session.delete(agent)
        self.session.commit()

    def test_producer_uuid(self, *args):
        """
        Test hybride property 'producer_uuid' of an Agent
        """
        agent = Agent(uuid='test-agent',
                      agent_port=5000)
        self.session.add_all([agent])
        self.session.commit()

        self.assertEqual(agent.producer_uuid, 'TEST-PRODUCER')

        # clean-up
        self.session.delete(agent)
        self.session.commit()

    @patch("openfactory.models.containers.DockerContainer.add_file")
    def test_create_container(self, mock_add_file, *args):
        """
        Test creation of Docker container for agent
        """
        agent = Agent(uuid='test-agent',
                      agent_port=6000)
        node = Node(
            node_name='manager',
            node_ip='123.456.7.891',
            network='test-net'
        )
        agent.node = node
        self.session.add_all([agent])
        self.session.commit()

        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)

        # check if created correctly container
        cont = agent.agent_container
        self.assertEqual(cont.image, config.MTCONNECT_AGENT_IMAGE)
        self.assertEqual(cont.name, 'test-agent')
        self.assertEqual(cont.command, 'mtcagent run agent.cfg')
        self.assertEqual(cont.cpus, 1)
        self.assertEqual(cont.node, node)
        self.assertEqual(cont.ports[0].container_port, '5000/tcp')
        self.assertEqual(cont.ports[0].host_port, 6000)

        # check container environment variables
        self.assertEqual(list(filter(lambda var: var.variable == 'MTC_AGENT_UUID', cont.environment))[0].value,
                         'TEST-AGENT')
        self.assertEqual(list(filter(lambda var: var.variable == 'ADAPTER_UUID', cont.environment))[0].value,
                         'TEST')
        self.assertEqual(list(filter(lambda var: var.variable == 'ADAPTER_IP', cont.environment))[0].value,
                         '123.456.7.500')
        self.assertEqual(list(filter(lambda var: var.variable == 'ADAPTER_PORT', cont.environment))[0].value,
                         '7878')

        # check files are added to container
        calls = mock_add_file.call_args_list
        self.assertTrue(call(device_file, '/home/agent/device.xml') in calls)
        self.assertTrue(call(config.MTCONNECT_AGENT_CFG_FILE, '/home/agent/agent.cfg') in calls)

        # clean-up
        self.session.delete(agent)
        self.session.delete(node)
        self.session.commit()
