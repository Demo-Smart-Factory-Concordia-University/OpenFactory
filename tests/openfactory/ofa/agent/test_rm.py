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
from openfactory.models.user_notifications import user_notify
from openfactory.exceptions import OFAException


@patch("openfactory.models.agents.swarm_manager_docker_client", return_value=mock.docker_client)
@patch("docker.DockerClient", return_value=mock.docker_client)
@patch("docker.APIClient", return_value=mock.docker_apiclient)
@patch("openfactory.models.agents.AgentKafkaProducer", return_value=mock.agent_kafka_producer)
class Test_ofa_agent_rm(TestCase):
    """
    Unit tests for ofa.agent.click_rm function
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
    def tearDown(self):
        """ Rollback all transactions """
        db.session.rollback()

    @classmethod
    def setUp(self):
        """ Reset mocks """
        user_notify.success.reset_mock()
        user_notify.info.reset_mock()
        user_notify.fail.reset_mock()

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
                       node=node,
                       device_xml='some1.xml',
                       adapter_ip='1.2.3.4',
                       adapter_port=7878)
        agent2 = Agent(uuid='TEST2-AGENT',
                       agent_port=6000,
                       node=node,
                       device_xml='some2.xml',
                       adapter_ip='1.2.3.4',
                       adapter_port=7878)
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

    def test_rm(self, *args):
        """
        Test if agent is removed
        """
        node, agent1, agent2 = self.setup_infrastructure()

        runner = CliRunner()
        result = runner.invoke(ofa.agent.click_rm, [agent1.uuid])
        self.assertEqual(result.exit_code, 0)

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
        node, agent1, agent2 = self.setup_infrastructure()

        runner = CliRunner()
        result = runner.invoke(ofa.agent.click_rm, [agent1.uuid])
        self.assertEqual(result.exit_code, 0)

        # check if user_notification called
        self.assertEqual(result.output,
                         'TEST1-AGENT removed successfully\n')

        # clean up
        self.cleanup()

    def test_detach(self, *args):
        """
        Test if producer of agent is removed
        """
        node, agent1, agent2 = self.setup_infrastructure()
        agent1.detach = Mock()

        runner = CliRunner()
        result = runner.invoke(ofa.agent.click_rm, [agent1.uuid])
        self.assertEqual(result.exit_code, 0)

        # check producer was removed
        agent1.detach.assert_called_once()

        # check if user_notification called
        self.assertEqual(result.output,
                         'TEST1-AGENT removed successfully\n')

        # clean up
        self.cleanup()

    def test_rm_with_wrong_agent_uuid(self, *args):
        """
        Test error message in case of wrong agent_uuid
        """
        runner = CliRunner()
        result = runner.invoke(ofa.agent.click_rm, ['none-existing-agent'])
        self.assertEqual(result.exit_code, 1)
        user_notify.fail.assert_called_once_with('No Agent none-existing-agent defined in OpenFactory')

    def test_rm_handle_OFAException(self, *args):
        """
        Test error message in case of OFAException during removal of an agent
        """
        node, agent1, agent2 = self.setup_infrastructure()

        # mock OFAException during a db.session.commit
        backup = db.session
        db.session = Mock()
        db.session.execute.return_value.one_or_none.return_value = [agent1]
        db.session.commit.side_effect = OFAException('Delete error')

        runner = CliRunner()
        result = runner.invoke(ofa.agent.click_rm, [agent1.uuid])

        # check OFAException is handled
        self.assertEqual(result.exit_code, 1)
        user_notify.fail.assert_called_once_with(f'Could not remove agent {agent1.uuid}: Delete error')

        # clean up
        db.session = backup
        self.cleanup()
