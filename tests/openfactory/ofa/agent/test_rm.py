import os
from unittest import TestCase
from unittest.mock import patch, Mock, call
from sqlalchemy import select

import tests.mocks as mock
import openfactory.ofa as ofa
from openfactory.ofa.db import db
from openfactory.models.base import Base
from openfactory.models.nodes import Node
from openfactory.models.agents import Agent
from openfactory.models.containers import DockerContainer


@patch("docker.DockerClient", return_value=mock.docker_client)
@patch("docker.APIClient", return_value=mock.docker_apiclient)
class Test_ofa_agent_rm(TestCase):
    """
    Unit tests for ofa.agent.rm function
    """

    @classmethod
    def setUpClass(cls):
        """ setup in memory sqlite db """
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
        """ rollback all transactions """
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
        Clean up all stacks and nodes
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

    def test_rm(self, *args):
        """
        Test if agent is removed
        """
        node, agent1, agent2 = self.setup_infrastructure()

        ofa.agent.rm(agent1)

        # check agent was removed
        query = select(Agent).where(Agent.uuid == "TEST1-AGENT")
        agent = db.session.execute(query).first()
        self.assertEqual(agent, None)

        # check other agents still present
        query = select(Agent).where(Agent.uuid == "TEST2-AGENT")
        agent = db.session.execute(query).first()
        self.assertEqual(agent[0], agent2)

        # clean up
        self.cleanup()

    def test_user_notification(self, *args):
        """
        Test if user_notification called correctly
        """
        mock_notification = Mock()
        node, agent1, agent2 = self.setup_infrastructure()

        ofa.agent.rm(agent1, user_notification=mock_notification)

        # check if user_notification called
        mock_notification.assert_called_once_with('TEST1-AGENT removed successfully')

        # clean up
        self.cleanup()

    def test_detach(self, *args):
        """
        Test if producer of agent is removed
        """
        mock_notification = Mock()
        node, agent1, agent2 = self.setup_infrastructure()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/mock_device.xml')
        agent1.create_container('123.456.7.500', 7878, device_file, 1)
        agent1.create_producer()

        ofa.agent.rm(agent1, user_notification=mock_notification)

        # check producer was removed
        query = select(DockerContainer).where(DockerContainer.name == "test1-producer")
        cont = db.session.execute(query).first()
        self.assertEqual(cont, None)

        # check if user_notification called
        calls = mock_notification.call_args_list
        self.assertEqual(calls[0], call('TEST1-PRODUCER removed successfully'))
        self.assertEqual(calls[1], call('TEST1-AGENT removed successfully'))

        # clean up
        self.cleanup()
