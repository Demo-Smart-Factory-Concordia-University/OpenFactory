import os
from unittest import TestCase
from unittest.mock import patch, Mock
from click.testing import CliRunner
from sqlalchemy import select

import tests.mocks as mock
import openfactory.ofa as ofa
from openfactory.ofa.db import db
from openfactory.models.base import Base
from openfactory.models.nodes import Node
from openfactory.models.agents import Agent


@patch("docker.DockerClient", return_value=mock.docker_client)
@patch("docker.APIClient", return_value=mock.docker_apiclient)
class Test_ofa_agent_start(TestCase):
    """
    Unit tests for ofa.agent.click_start
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

    @classmethod
    def tearDown(self):
        """ Rollback all transactions """
        db.session.rollback()

    def setup_infrastructure(self, *args):
        """
        Setup base infrastructure
        """
        node = Node(
            node_name='manager',
            node_ip='123.456.7.891',
            network='test-net'
        )
        agent1 = Agent(uuid='TEST1-AGENT',
                       agent_port=6000,
                       node=node)
        agent2 = Agent(uuid='TEST2-AGENT',
                       agent_port=6000,
                       node=node)
        db.session.add_all([node, agent1, agent2])
        db.session.commit()
        return node, agent1, agent2

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

    def test_start(self, *args):
        """
        Test if Docker container is started
        """
        node, agent1, agent2 = self.setup_infrastructure()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/mock_device.xml')
        agent1.create_container('123.456.7.500', 7878, device_file, 1)
        agent1.agent_container.start = Mock()

        runner = CliRunner()
        result = runner.invoke(ofa.agent.click_start, [agent1.uuid])
        self.assertEqual(result.exit_code, 0)

        # check agent Docker container was started
        agent1.agent_container.start.assert_called_once()

        # clean up
        self.cleanup()

    def test_start_with_producer(self, *args):
        """
        Test if Docker container is started
        """
        node, agent1, agent2 = self.setup_infrastructure()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/mock_device.xml')
        agent1.create_container('123.456.7.500', 7878, device_file, 1)
        agent1.create_producer()
        agent1.agent_container.start = Mock()
        agent1.producer_container.start = Mock()

        runner = CliRunner()
        result = runner.invoke(ofa.agent.click_start, [agent1.uuid])
        self.assertEqual(result.exit_code, 0)

        # check agent Docker container and producer was started
        agent1.agent_container.start.assert_called_once()
        agent1.producer_container.start.assert_called_once()

        # clean up
        self.cleanup()

    def test_start_with_wrong_agent_uuid(self, *args):
        """
        Test error message in case of wrong agent_uuid
        """
        runner = CliRunner()
        result = runner.invoke(ofa.agent.click_start, ['none-existing-agent'])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.output,
                         'No Agent none-existing-agent defined in OpenFactory\n')
