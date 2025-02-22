from unittest import TestCase
from unittest.mock import patch, Mock
from sqlalchemy import select
from mtc2kafka.connectors import MTCSourceConnector

import tests.mocks as mock
import openfactory.config as config
from openfactory.ofa.db import db
from openfactory.docker.docker_access_layer import dal
from openfactory.models.agents import AgentKafkaProducer
from openfactory.models.base import Base
from openfactory.models.agents import Agent


@patch("docker.DockerClient", return_value=mock.docker_client)
@patch("openfactory.utils.assets.Producer", return_value=Mock())
@patch("openfactory.utils.assets.KSQL", return_value=Mock())
@patch("openfactory.models.agents.KSQL", return_value=Mock())
@patch("mtc2kafka.connectors.MTCSourceConnector")
@patch("mtc2kafka.connectors.MTCSourceConnector.send_producer_availability")
@patch("mtc2kafka.connectors.MTCSourceConnector.send_agent_availability")
class TestAgentKafkaProducer(TestCase):
    """
    Unit tests for AgentKafkaProducer
    """

    @classmethod
    def setUpClass(cls):
        """ Setup in memory sqlite db """
        print("Setting up in memory sqlite db")
        db.conn_uri = 'sqlite:///:memory:'
        db.connect()
        Base.metadata.create_all(db.engine)
        dal.docker_client = mock.docker_client

    @classmethod
    def tearDownClass(cls):
        print("\nTear down in memory sqlite db")
        Base.metadata.drop_all(db.engine)
        db.session.close()

    def cleanup(self, *args):
        """
        Clean up all agents
        """
        for agent in db.session.scalars(select(Agent)):
            db.session.delete(agent)
        db.session.commit()

    def test_class_parent(self, *args):
        """
        Test parent of class is MTCSourceConnector
        """
        self.assertEqual(AgentKafkaProducer.__bases__[0], MTCSourceConnector)

    def test_bootstrap_servers(self, *args):
        """
        Test bootstrap_servers
        """
        self.assertEqual(AgentKafkaProducer.bootstrap_servers, [config.KAFKA_BROKER])

    def test_init(self, *args):
        """
        Test init of AgentKafkaProducer
        """
        agent = Agent(uuid='TEST-AGENT',
                      agent_port=6000,
                      device_xml='some.xml',
                      adapter_ip='1.2.3.4',
                      adapter_port=7878)
        db.session.add_all([agent])
        db.session.commit()

        kafka_producer = AgentKafkaProducer(agent)

        # check attributes
        self.assertEqual(kafka_producer.mtc_agent, 'test-agent:5000')
        self.assertEqual(kafka_producer.kafka_producer_uuid, 'TEST-PRODUCER')

        # clean-up
        self.cleanup()
