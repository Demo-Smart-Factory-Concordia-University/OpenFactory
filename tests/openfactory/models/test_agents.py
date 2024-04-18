import os
from unittest import TestCase
from unittest.mock import patch, call, Mock
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from httpx import HTTPError
from paramiko.ssh_exception import SSHException

import openfactory.config as config
from openfactory.exceptions import OFAException
from openfactory.ofa.db import db
from openfactory.models.user_notifications import user_notify
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

    def tearDown(self):
        """ Rollback all transactions """
        db.session.rollback()

    def setup_agent(self, *args):
        """
        Setup an agent
        """
        agent = Agent(uuid='TEST-AGENT',
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
        Test setup of an Agent
        """
        self.setup_agent()

        query = select(Agent).where(Agent.uuid == "TEST-AGENT")
        agent = db.session.execute(query).first()
        self.assertEqual(agent[0].uuid, 'TEST-AGENT')
        self.assertEqual(agent[0].agent_port, 5000)
        self.assertEqual(agent[0].external, False)

        # clean-up
        self.cleanup()

    def test_agent_teardown(self, *args):
        """
        Test tear down of an Agent
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)
        agent.create_producer()
        container_name = agent.agent_container.name
        producer_name = agent.producer_container.name

        # tear down agent
        db.session.delete(agent)
        db.session.commit()

        # check Docker container was removed
        query = select(DockerContainer).where(DockerContainer.name == container_name)
        cont = db.session.execute(query).first()
        self.assertEqual(cont, None)

        # check producer was removed
        query = select(DockerContainer).where(DockerContainer.name == producer_name)
        cont = db.session.execute(query).first()
        self.assertEqual(cont, None)

        # clean-up
        self.cleanup()

    def test_agent_teardown_notifications(self, *args):
        """
        Test user notifications when tear down of an Agent
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)
        agent.create_producer()

        # tear down agent
        user_notify.success.reset_mock()
        db.session.delete(agent)
        db.session.commit()

        # check notfications were emitted
        calls = user_notify.success.call_args_list
        self.assertEqual(calls[0], call('Kafka producer TEST-PRODUCER removed successfully'))
        self.assertEqual(calls[1], call('Agent TEST-AGENT removed successfully'))

        # agent without producer
        self.cleanup()
        agent = self.setup_agent()
        agent.create_container('123.456.7.500', 7878, device_file, 1)

        # tear down agent
        user_notify.success.reset_mock()
        db.session.delete(agent)
        db.session.commit()

        # check notfications were emitted
        user_notify.success.called_once_with('Agent TEST-AGENT removed successfully')

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

    def test_start(self, *args):
        """
        Test if Docker container is started
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)
        agent.agent_container.start = Mock()
        agent.start()

        # check agent Docker container was started
        agent.agent_container.start.assert_called_once()

        # clean up
        self.cleanup()

    def test_start_with_producer(self, *args):
        """
        Test if Docker container is started
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)
        agent.create_producer()
        agent.agent_container.start = Mock()
        agent.producer_container.start = Mock()

        agent.start()

        # check agent Docker container and producer was started
        agent.agent_container.start.assert_called_once()
        agent.producer_container.start.assert_called_once()

        # clean up
        self.cleanup()

    def test_start_user_notification(self, *args):
        """
        Test if user_notification called correctly in start method
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)
        user_notify.success.reset_mock()
        agent.start()

        # check if user_notification called
        user_notify.success.assert_called_once_with('Agent TEST-AGENT started successfully')

        # add producer
        agent.create_producer()
        user_notify.success.reset_mock()
        agent.start()

        # check if user_notification called
        calls = user_notify.success.call_args_list
        self.assertEqual(calls[0], call('Kafka producer TEST-PRODUCER started successfully'))
        self.assertEqual(calls[1], call('Agent TEST-AGENT started successfully'))

        # clean up
        self.cleanup()

    def test_stop(self, *args):
        """
        Test if Docker container is stopped
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)
        agent.agent_container.stop = Mock()
        agent.stop()

        # check agent Docker container was started
        agent.agent_container.stop.assert_called_once()

        # clean up
        self.cleanup()

    def test_stop_user_notification(self, *args):
        """
        Test if user_notification called correctly in stop method
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)
        user_notify.success.reset_mock()
        agent.stop()

        # check if user_notification called
        user_notify.success.assert_called_once_with('Agent TEST-AGENT stopped successfully')

        # clean up
        self.cleanup()

    def test_attach(self, *args):
        """
        Test if producer is attached
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)

        agent.create_ksqldb_tables = Mock()
        agent.attach(cpus=3)

        # check ksqldb_tables created
        agent.create_ksqldb_tables.assert_called_once()

        # check producer was created
        cont = agent.producer_container
        self.assertEqual(cont.image, config.MTCONNECT_PRODUCER_IMAGE)
        self.assertEqual(cont.name, 'test-producer')
        self.assertEqual(cont.cpus, 3)
        self.assertEqual(cont.node, agent.node)
        self.assertEqual(cont.ports, [])

        # check container was started
        agent.producer_container.container.start.assert_called_once()

        # clean up
        self.cleanup()

    def test_attach_no_container_error(self, *args):
        """
        Test if error is raised in attach when no Agent container
        """
        agent = self.setup_agent()

        # check OFAException raised if no Agent container
        self.assertRaises(OFAException, agent.attach)

        # clean up
        self.cleanup()

    @patch('pyksql.ksql.KSQL.__init__', side_effect=HTTPError('test'))
    def test_attach_ksqlDB_error(self, *args):
        """
        Test if error is raised in attach if ksqlDB cannot be reached
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)

        # check OFAException raised if ksqlDB can not be reached
        self.assertRaises(OFAException, agent.attach)

        # clean up
        self.cleanup()

    def test_attach_producer_error(self, *args):
        """
        Test if errors is raised in attach if producer container cannot be created
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)

        agent.create_ksqldb_tables = Mock()
        agent.create_producer = Mock(side_effect=SSHException('test'))

        # check OFAException raised if ksqlDB can not be reached
        self.assertRaises(OFAException, agent.attach)

        # clean up
        self.cleanup()

    def test_detach(self, *args):
        """
        Test if producer is removed
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)
        agent.create_producer()
        producer_name = agent.producer_container.name
        agent.detach()

        # check producer was removed
        self.assertEqual(agent.producer_container, None)
        query = select(DockerContainer).where(DockerContainer.name == producer_name)
        cont = db.session.execute(query).first()
        self.assertEqual(cont, None)

        # check detach can be used even if no producer is present
        agent.detach()

        # clean up
        self.cleanup()

    def test_detach_user_notification(self, *args):
        """
        Test if user_notification called correctly in detach method
        """
        agent = self.setup_agent()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)
        agent.create_producer()
        user_notify.success.reset_mock()
        agent.detach()

        # check if user_notification called
        user_notify.success.assert_called_once_with('Kafka producer TEST-PRODUCER removed successfully')

        # clean up
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
