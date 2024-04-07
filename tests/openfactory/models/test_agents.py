import os
from unittest import TestCase
from unittest.mock import patch, call
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import openfactory.config as config
from openfactory.ofa.db import db
from openfactory.models.base import Base
from openfactory.models.nodes import Node
from openfactory.models.agents import Agent
from openfactory.models.containers import DockerContainer
import tests.mocks as mock


@patch("docker.DockerClient", return_value=mock.docker_client)
class TestAgent(TestCase):
    """
    Unit tests for Agent model
    """

    @classmethod
    def setUpClass(cls):
        """ Setup in memory sqlite db """
        print("Setting up in memory sqlite db")
        db.conn_uri = 'sqlite:///:memory:'
        db.connect()
        Base.metadata.create_all(db.engine)

    @classmethod
    def tearDownClass(cls):
        print("\nTear down in memory sqlite db")
        Base.metadata.drop_all(db.engine)
        db.session.close()

    def tearDown(self):
        """ Rollback all transactions """
        db.session.rollback()
        self.cleanup()

    def setup_agent(self, *args):
        """
        Setup an agent
        """
        agent = Agent(uuid='test-agent',
                      agent_port=5000)
        node = Node(
            node_name='manager',
            node_ip='123.456.7.891',
            network='test-net'
        )
        agent.node = node
        db.session.add_all([node, agent])
        db.session.commit()
        return agent

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
        self.setup_agent()

        query = select(Agent).where(Agent.uuid == "test-agent")
        agent = db.session.execute(query).first()
        self.assertEqual(agent[0].uuid, 'test-agent')
        self.assertEqual(agent[0].agent_port, 5000)
        self.assertEqual(agent[0].external, False)

        # clean-up
        self.cleanup()

    def test_agent_uuid_unique(self, *args):
        """
        Test Agent.uuid is required to be unique
        """
        agent1 = Agent(uuid='test-agent',
                       agent_port=5000)
        agent2 = Agent(uuid='test-agent',
                       agent_port=6000)
        db.session.add_all([agent1, agent2])
        self.assertRaises(IntegrityError, db.session.commit)

    def test_agent_url(self, *args):
        """
        Test hybride property 'agent_url' of an Agent
        """
        agent = self.setup_agent()

        self.assertEqual(agent.agent_url, '123.456.7.891')

        # clean-up
        self.cleanup()

    def test_device_uuid(self, *args):
        """
        Test hybride property 'device_uuid' of an Agent
        """
        agent = self.setup_agent()

        self.assertEqual(agent.device_uuid, 'TEST')

        # clean-up
        self.cleanup()

    def test_producer_uuid(self, *args):
        """
        Test hybride property 'producer_uuid' of an Agent
        """
        agent = self.setup_agent()

        self.assertEqual(agent.producer_uuid, 'TEST-PRODUCER')

        # clean-up
        self.cleanup()

    @patch("openfactory.models.containers.DockerContainer.add_file")
    def test_create_container(self, mock_add_file, *args):
        """
        Test creation of Docker container for agent
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)

        # check if created correctly container
        cont = agent.agent_container
        self.assertEqual(cont.image, config.MTCONNECT_AGENT_IMAGE)
        self.assertEqual(cont.name, 'test-agent')
        self.assertEqual(cont.command, 'mtcagent run agent.cfg')
        self.assertEqual(cont.cpus, 1)
        self.assertEqual(cont.node, agent.node)
        self.assertEqual(cont.ports[0].container_port, '5000/tcp')
        self.assertEqual(cont.ports[0].host_port, 5000)

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
        self.cleanup()

    def test_container(self, *args):
        """
        Test hybrid_property 'container'
        """
        agent = self.setup_agent()

        # check container property
        self.assertEqual(agent.container, 'test-agent')

        # clean-up
        self.cleanup()

    def test_status(self, *args):
        """
        Test hybrid_property 'status'
        """
        agent = self.setup_agent()

        # check container satus
        self.assertEqual(agent.status, 'No container')

        # create container
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)

        # check container satus
        self.assertEqual(agent.status, 'running')

        # clean-up
        self.cleanup()

    def test_create_producer(self, *args):
        """
        Test creation of Kafka producer for agent
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)
        agent.create_producer(2)

        # check if created correctly container
        cont = agent.producer_container
        self.assertEqual(cont.image, config.MTCONNECT_PRODUCER_IMAGE)
        self.assertEqual(cont.name, 'test-producer')
        self.assertEqual(cont.cpus, 2)
        self.assertEqual(cont.node, agent.node)
        self.assertEqual(cont.ports, [])

        # check container environment variables
        self.assertEqual(list(filter(lambda var: var.variable == 'KAFKA_BROKER', cont.environment))[0].value,
                         config.KAFKA_BROKER)
        self.assertEqual(list(filter(lambda var: var.variable == 'KAFKA_PRODUCER_UUID', cont.environment))[0].value,
                         'TEST-PRODUCER')
        self.assertEqual(list(filter(lambda var: var.variable == 'MTC_AGENT', cont.environment))[0].value,
                         'test-agent:5000')

        # clean-up
        self.cleanup()

    def test_attached(self, *args):
        """
        Test hybrid_property 'attached'
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)

        # check attached property
        self.assertEqual(agent.attached, 'no')

        # attach producer
        agent.create_producer()

        # check attached property
        self.assertEqual(agent.attached, 'yes')

        # clean-up
        self.cleanup()

    def test_container_removed(self, *args):
        """
        Test if Docker container of agent is removed when agent removed
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)
        db.session.delete(agent)

        # check agent container is removed
        query = select(DockerContainer).where(DockerContainer.name == "test-agent")
        cont = db.session.execute(query).first()
        self.assertEqual(cont, None)

        # clean-up
        self.cleanup()

    def test_producer_removed(self, *args):
        """
        Test if Kafka producer of agent is removed when agent removed
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)
        agent.create_producer()
        db.session.delete(agent)

        # check Kafka producer is removed
        query = select(DockerContainer).where(DockerContainer.name == "test-producer")
        cont = db.session.execute(query).first()
        self.assertEqual(cont, None)

        # clean-up
        self.cleanup()
