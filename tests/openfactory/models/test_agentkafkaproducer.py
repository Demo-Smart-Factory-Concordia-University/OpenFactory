import os
from unittest import TestCase
from unittest.mock import patch
from sqlalchemy import select
from mtc2kafka.connectors import MTCSourceConnector

import tests.mocks as mock
import openfactory.config as config
from openfactory.ofa.db import db
from openfactory.models.agents import AgentKafkaProducer
from openfactory.models.base import Base
from openfactory.models.nodes import Node
from openfactory.models.agents import Agent


@patch("docker.DockerClient", return_value=mock.docker_client)
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

    @classmethod
    def tearDownClass(cls):
        print("\nTear down in memory sqlite db")
        Base.metadata.drop_all(db.engine)
        db.session.close()

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
        node = Node(
            node_name='manager',
            node_ip='123.456.7.891',
            network='test-net'
        )
        agent = Agent(uuid='TEST-AGENT',
                      agent_port=6000,
                      node=node,
                      device_xml='some.xml')
        db.session.add_all([node, agent])
        db.session.commit()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)

        kafka_producer = AgentKafkaProducer(agent)

        # check attributes
        self.assertEqual(kafka_producer.mtc_agent, 'test-agent:5000')
        self.assertEqual(kafka_producer.kafka_producer_uuid, 'TEST-PRODUCER')

        # clean-up
        self.cleanup()
