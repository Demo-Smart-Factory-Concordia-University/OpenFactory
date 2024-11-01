import os
import docker
from unittest import TestCase
from unittest.mock import patch, call, Mock, mock_open
import docker.errors
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from httpx import HTTPError

from openfactory.exceptions import OFAException
from openfactory.ofa.db import db
from openfactory.docker.docker_access_layer import dal
from openfactory.models.user_notifications import user_notify
from openfactory.models.base import Base
from openfactory.models.nodes import Node
from openfactory.models.agents import Agent, agent_before_delete
import tests.mocks as mock


@patch("openfactory.models.agents.AgentKafkaProducer", return_value=mock.agent_kafka_producer)
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
        mock.docker_services.reset_mock()
        user_notify.success.reset_mock()
        user_notify.fail.reset_mock()

    def tearDown(self):
        """ Rollback all transactions """
        db.session.rollback()

    def setup_agent(self, *args):
        """
        Setup an agent
        """
        xml_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'mocks/mock_device.xml')
        agent = Agent(uuid='TEST-AGENT',
                      agent_port=5000,
                      device_xml=xml_file,
                      adapter_ip='1.2.3.4',
                      adapter_port=7878,
                      constraints=['node.labels.type == ofa'])
        db.session.add_all([agent])
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

    @patch("openfactory.models.agents.Agent.status", return_value='running')
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
        agent.stop = Mock()
        agent.detach = Mock()

        # tear down agent
        db.session.delete(agent)
        db.session.commit()

        # check Docker service was removed
        agent.stop.assert_called_once()

        # check producer service was removed
        agent.detach.assert_called_once()

        # clean-up
        self.cleanup()

    def test_agent_teardown_notifications(self, *args):
        """
        Test user notifications when tear down of an Agent
        """
        agent = self.setup_agent()

        # tear down agent
        user_notify.success.reset_mock()
        db.session.delete(agent)
        db.session.commit()

        # check notfications were emitted
        calls = user_notify.success.call_args_list
        self.assertIn(call('Agent TEST-AGENT removed successfully'), calls)
        self.assertIn(call('Agent TEST-AGENT stopped successfully'), calls)
        self.assertIn(call('Kafka producer for agent TEST-AGENT stopped successfully'), calls)

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

    def test_load_device_xml(self, *args):
        """
        Test loading of device model based on URI
        """
        agent = self.setup_agent()
        xml_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'mocks/mock_device.xml')
        with open(xml_file, 'r') as file:
            expected = file.read()

        self.assertEqual(agent.load_device_xml(), expected)

        # clean-up
        self.cleanup()

    @patch("openfactory.models.agents.open_ofa")
    def test_load_device_xml_use_open_ofa(self, mock_open_ofa, *args):
        """
        Test loading of device model based on URI uses open_ofa
        """
        agent = self.setup_agent()
        xml_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'mocks/mock_device.xml')
        agent.load_device_xml()
        mock_open_ofa.assert_called_with(xml_file)

        # clean-up
        self.cleanup()

    def test_load_device_xml_does_not_exist(self, *args):
        """
        Test if user_notify.fail called when device file does not exist
        """
        agent = self.setup_agent()
        agent.device_xml = '/this/does/not/exist'
        agent.load_device_xml()
        user_notify.fail.assert_called_once_with("Could not load XML device model for TEST-AGENT.\n[Errno 2] No such file or directory: '/this/does/not/exist'")

        # clean-up
        self.cleanup()

    def test_start(self, *args):
        """
        Test if Agent deploy called
        """
        agent = self.setup_agent()
        agent.deploy_agent = Mock()
        agent.attach = Mock()
        agent.start()
        agent.deploy_agent.assert_called_once()
        agent.attach.assert_called_once()

        # clean up
        self.cleanup()

    def test_start_user_notification(self, *args):
        """
        Test if user_notification called correctly in start method
        """
        agent = self.setup_agent()
        agent.deploy_agent = Mock()
        agent.deploy_producer = Mock()
        user_notify.success.reset_mock()
        agent.start()

        # check if user_notification called
        user_notify.success.assert_called_once_with('Agent TEST-AGENT started successfully')

        # clean up
        self.cleanup()

    def test_stop(self, *args):
        """
        Test if Docker container is stopped
        """
        agent = self.setup_agent()
        agent.stop()

        # check agent service was removed
        mock.docker_services.get.assert_called_once_with('test-agent')
        mock.docker_service.remove.assert_called_once()

        # clean up
        self.cleanup()

    def test_stop_user_notification(self, *args):
        """
        Test if user_notification called correctly in stop method
        """
        agent = self.setup_agent()
        user_notify.success.reset_mock()
        agent.stop()

        # check if user_notification called
        user_notify.success.assert_called_once_with('Agent TEST-AGENT stopped successfully')

        # clean up
        self.cleanup()

    def test_stop_send_unavailable(self, *args):
        """
        Test if UNAVAILABLE sent to Kafka
        """
        agent = self.setup_agent()
        agent.kafka_producer = Mock()
        agent.kafka_producer.send_agent_availability = Mock()
        agent.stop()

        # check if UNAVAILABLE sent to Kafka
        agent.kafka_producer.send_agent_availability.assert_called_once_with('UNAVAILABLE')

        # clean up
        self.cleanup()

    def test_attach(self, *args):
        """
        Test if producer is attached
        """
        agent = self.setup_agent()
        agent.create_ksqldb_tables = Mock()
        agent.deploy_producer = Mock()
        agent.attach()

        # check ksqldb_tables created
        agent.create_ksqldb_tables.assert_called_once()

        # check producer was deployed
        agent.deploy_producer.assert_called_once()

        # clean up
        self.cleanup()

    @patch('pyksql.ksql.KSQL.__init__', side_effect=HTTPError('test'))
    def test_attach_ksqlDB_error(self, *args):
        """
        Test if error is raised in attach if ksqlDB cannot be reached
        """
        agent = self.setup_agent()

        # check OFAException raised if ksqlDB can not be reached
        self.assertRaises(OFAException, agent.attach)

        # clean up
        self.cleanup()

    def test_detach(self, *args):
        """
        Test if producer service is removed
        """
        agent = self.setup_agent()
        agent.detach()

        # check producer service was removed
        mock.docker_services.get.assert_called_once_with('test-producer')
        mock.docker_service.remove.assert_called_once()

        # clean up
        self.cleanup()

    def test_detach_user_notification(self, *args):
        """
        Test if user_notification called correctly in detach method
        """
        agent = self.setup_agent()
        user_notify.success.reset_mock()
        agent.detach()

        # check if user_notification called
        user_notify.success.assert_called_once_with('Kafka producer for agent TEST-AGENT stopped successfully')

        # clean up
        self.cleanup()

    def test_detach_send_unavailable(self, *args):
        """
        Test if UNAVAILABLE sent to Kafka
        """
        agent = self.setup_agent()
        agent.kafka_producer = Mock()
        agent.kafka_producer.send_producer_availability = Mock()
        agent.detach()

        # check if UNAVAILABLE sent to Kafka
        agent.kafka_producer.send_producer_availability.assert_called_once_with('UNAVAILABLE')

        # clean up
        self.cleanup()

    def test_deploy_agent_correct_client(self, *args):
        """
        Test if correct Docker client is used
        """
        agent = self.setup_agent()
        agent.deploy_agent()
        dal.docker_client.services.create.assert_called_once()

        # clean up
        self.cleanup()

    @patch('openfactory.models.agents.open', new_callable=mock_open, read_data='mock_agent_cfg')
    @patch('openfactory.models.agents.docker.types.EndpointSpec')
    @patch("openfactory.models.agents.config")
    def test_deploy_agent(self, mock_config, mock_endpoint_spec, *args):
        """
        Test creation of Docker swarm service for agent
        """

        mock_config.MTCONNECT_AGENT_IMAGE = 'mock_agent_image'
        mock_config.MTCONNECT_AGENT_CFG_FILE = '/path/to/mock/agent.cfg'
        mock_config.OPENFACTORY_NETWORK = 'mock_network'
        mock_endpoint_spec.return_value = Mock()

        agent = self.setup_agent()
        agent.load_device_xml = Mock(return_value='mock_device_xml')
        agent.deploy_agent()

        mock.docker_services.create.assert_called_once_with(
            image='mock_agent_image',
            command="sh -c 'printf \"%b\" \"$XML_MODEL\" > device.xml; printf \"%b\" \"$AGENT_CFG_FILE\" > agent.cfg; mtcagent run agent.cfg'",
            name='test-agent',
            mode={"Replicated": {"Replicas": 1}},
            env=[
                'MTC_AGENT_UUID=TEST-AGENT',
                'ADAPTER_UUID=TEST',
                'ADAPTER_IP=1.2.3.4',
                'ADAPTER_PORT=7878',
                'XML_MODEL=mock_device_xml',
                'AGENT_CFG_FILE=mock_agent_cfg'
            ],
            endpoint_spec=mock_endpoint_spec.return_value,
            networks=['mock_network'],
            resources={
                "Limits": {"NanoCPUs": int(1000000000 * 1.0)},
                "Reservations": {"NanoCPUs": int(1000000000 * 0.5)}
            },
            constraints=['node.labels.type == ofa']
        )

        # clean up
        self.cleanup()

    @patch("openfactory.models.agents.config")
    def test_deploy_agent_no_agent_config_file(self, mock_config, *args):
        """
        Test if error raised when agent config file is missing
        """

        mock_config.MTCONNECT_AGENT_CFG_FILE = '/this/does/not/exist/agent.cfg.'

        agent = self.setup_agent()
        self.assertRaises(OFAException, agent.deploy_agent)

        # clean up
        self.cleanup()

    @patch("openfactory.models.agents.config")
    def test_create_adapter(self, mock_config, *args):
        """
        Test creation of Docker container for an adapter
        """
        mock_config.OPENFACTORY_NETWORK = 'mock_network'
        agent = self.setup_agent()
        env = ['MyVar=MyValue', 'MyOtherVar=MyOtherValue']
        agent.create_adapter('someone/some_img', cpus_limit=1.5, cpus_reservation=1.0, environment=env)

        # check if created correctly service
        mock.docker_services.create.assert_called_once_with(
            image='someone/some_img',
            name='test-adapter',
            mode={"Replicated": {"Replicas": 1}},
            env=env,
            networks=['mock_network'],
            resources={
                "Limits": {"NanoCPUs": int(1000000000 * 1.5)},
                "Reservations": {"NanoCPUs": int(1000000000 * 1.0)}
            }
        )

        # clean-up
        self.cleanup()

    def test_remove_adapter(self, *args):
        """
        Test remove_adapter
        """
        agent = self.setup_agent()
        agent.remove_adapter()

        mock.docker_services.get.assert_called_once_with('test-adapter')
        mock.docker_service.remove.assert_called_once()

        # clean-up
        self.cleanup()

    def test_remove_adapter_called(self, *args):
        """
        Test adapter service removed when agent removed
        """
        agent = self.setup_agent()
        agent.remove_adapter = Mock()
        db.session.delete(agent)
        db.session.commit()

        agent.remove_adapter.assert_called_once()

        # clean-up
        self.cleanup()

    @patch.object(Agent, 'top_task', new_callable=Mock(return_value={'Status': {'State': 'some state'}}))
    def test_status(self, *args):
        """
        Test hybrid_property 'status'
        """
        agent = self.setup_agent()
        self.assertEqual(agent.status, 'Some state')

        # clean-up
        self.cleanup()

    def test_status_service_does_not_exist(self, *args):
        """
        Test hybrid_property 'status' when service does not exist
        """
        agent = self.setup_agent()

        # check container satus when service does not exist
        dal.docker_client.services.get.side_effect = docker.errors.NotFound('mock no service running')
        self.assertEqual(agent.status, 'Stopped')

        # clean-up
        dal.docker_client.services.get.side_effect = None
        self.cleanup()

    @patch("openfactory.models.agents.config")
    def test_deploy_producer(self, mock_config, *args):
        """
        Test creation of Docker swarm service for producer
        """

        mock_config.MTCONNECT_PRODUCER_IMAGE = 'mock_producer_image'
        mock_config.KAFKA_BROKER = 'mock_broker'
        mock_config.OPENFACTORY_NETWORK = 'mock_network'

        agent = self.setup_agent()
        agent.deploy_producer()

        mock.docker_services.create.assert_called_once_with(
            image='mock_producer_image',
            name='test-producer',
            mode={"Replicated": {"Replicas": 1}},
            env=[
                'KAFKA_BROKER=mock_broker',
                'KAFKA_PRODUCER_UUID=TEST-PRODUCER',
                'MTC_AGENT=test-agent:5000',
            ],
            networks=['mock_network'],
            constraints=['node.labels.type == ofa']
        )

        # clean up
        self.cleanup()

    def test_services_removed(self, *args):
        """
        Test if Kafka producer and agent services are removed when agent deleted
        """
        agent = self.setup_agent()
        agent.detach = Mock()
        agent.stop = Mock()
        agent_before_delete(None, None, agent)

        # check services were stopped
        agent.detach.assert_called_once()
        agent.stop.assert_called_once()

        # clean-up
        self.cleanup()

    @patch.object(Agent, 'status', new_callable=Mock(return_value='running'))
    def test_kafka_producer_setup_on_load(self, *args):
        """
        Test if kafka_producer setup when agent loaded from database
        """
        self.setup_agent()

        # reload same instance
        db.session.close()
        db.session = Session(db.engine)
        query = select(Agent).where(Agent.uuid == "TEST-AGENT")
        agent_reload = db.session.execute(query).one()
        agent_reload = agent_reload[0]

        # check kafka_producer setup
        self.assertNotEqual(agent_reload.kafka_producer, None)

        # clean-up
        self.cleanup()

    def test_unavailable_sent_on_delete(self, *args):
        """
        Test if Kafka messages sent when agent deleted
        """
        agent = self.setup_agent()
        agent.create_ksqldb_tables = Mock()
        agent.attach()
        db.session.delete(agent)

        # check Kafka messages sent
        agent.kafka_producer.send_producer_availability.called_once_with('UNAVAILABLE')
        agent.kafka_producer.send_agent_availability.called_once_with('UNAVAILABLE')

        # clean-up
        self.cleanup()
