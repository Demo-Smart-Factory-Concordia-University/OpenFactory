from unittest import TestCase
from unittest.mock import patch, Mock
from click.testing import CliRunner
from sqlalchemy import select

import tests.mocks as mock
import openfactory.ofa as ofa
from openfactory.ofa.db import db
from openfactory.docker.docker_access_layer import dal
from openfactory.models.base import Base
from openfactory.models.agents import Agent
from openfactory.models.user_notifications import user_notify
from openfactory.exceptions import OFAException


@patch("openfactory.models.agents.AgentKafkaProducer", return_value=mock.agent_kafka_producer)
@patch("docker.DockerClient", return_value=mock.docker_client)
@patch("docker.APIClient", return_value=mock.docker_apiclient)
class Test_ofa_agent_stop(TestCase):
    """
    Unit tests for ofa.agent.click_stop
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
        """ Reset mocks """
        user_notify.success.reset_mock()
        user_notify.info.reset_mock()
        user_notify.fail.reset_mock()

    @classmethod
    def tearDown(self):
        """ Rollback all transactions """
        db.session.rollback()

    def setup_infrastructure(self, *args):
        """
        Setup base infrastructure
        """
        agent1 = Agent(uuid='TEST1-AGENT',
                       agent_port=6000,
                       device_xml='some1.xml',
                       adapter_ip='1.2.3.4',
                       adapter_port=7878)
        agent2 = Agent(uuid='TEST2-AGENT',
                       agent_port=6000,
                       device_xml='some2.xml',
                       adapter_ip='1.2.3.4',
                       adapter_port=7878)
        db.session.add_all([agent1, agent2])
        db.session.commit()
        return agent1, agent2

    def cleanup(self, *args):
        """
        Clean up all agents
        """
        for agent in db.session.scalars(select(Agent)):
            db.session.delete(agent)
        db.session.commit()

    def test_stop(self, *args):
        """
        Test if Docker service is stopped
        """
        agent1, _ = self.setup_infrastructure()
        agent1.stop = Mock()

        runner = CliRunner()
        result = runner.invoke(ofa.agent.click_stop, [agent1.uuid])
        self.assertEqual(result.exit_code, 0)

        # check agent Docker container was started
        agent1.stop.assert_called_once()

        # clean up
        self.cleanup()

    def test_stop_with_wrong_agent_uuid(self, *args):
        """
        Test error message in case of wrong agent_uuid
        """
        runner = CliRunner()
        result = runner.invoke(ofa.agent.click_stop, ['none-existing-agent'])
        self.assertEqual(result.exit_code, 1)
        user_notify.fail.assert_called_once_with('No Agent none-existing-agent defined in OpenFactory')

    def test_stop_handle_OFAException(self, *args):
        """
        Test error message in case of OFAException during stop of an agent
        """
        # mock OFAException during agent.stop
        agent = Mock()
        agent.uuid = 'TEST-AGENT'
        agent.stop = Mock(side_effect=OFAException('Start error'))

        # return mocked agent in db.session.execute(query).one_or_none()
        backup = db.session
        db.session = Mock()
        db.session.execute.return_value.one_or_none.return_value = [agent]

        runner = CliRunner()
        result = runner.invoke(ofa.agent.click_stop, [agent.uuid])
        self.assertEqual(result.exit_code, 1)
        user_notify.fail.assert_called_once_with(f'Could not stop agent {agent.uuid}: Start error')

        # clean up
        db.session = backup
        self.cleanup()
