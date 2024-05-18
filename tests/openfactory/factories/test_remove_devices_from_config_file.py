import os
from unittest import TestCase
from unittest.mock import patch, Mock, call
from sqlalchemy import select

import tests.mocks as mock
from openfactory.ofa.db import db
from openfactory.factories import create_infrastack
from openfactory.factories import create_agents_from_config_file
from openfactory.factories import remove_devices_from_config_file
from openfactory.models.user_notifications import user_notify
from openfactory.models.base import Base
from openfactory.models.agents import Agent
from openfactory.models.containers import DockerContainer
from openfactory.models.infrastack import InfraStack
from openfactory.models.nodes import Node


@patch("openfactory.models.agents.AgentKafkaProducer", return_value=mock.agent_kafka_producer)
@patch("docker.DockerClient", return_value=mock.docker_client)
@patch("docker.APIClient", return_value=mock.docker_apiclient)
class Test_remove_devices_from_config_file(TestCase):
    """
    Unit tests for remove_agents_from_config_file
    """

    @classmethod
    def setUpClass(cls):
        """ setup in memory sqlite db """
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
        """ Reset mocks """
        user_notify.success.reset_mock()
        user_notify.info.reset_mock()
        user_notify.fail.reset_mock()

    @classmethod
    def tearDown(self):
        """ rollback all transactions """
        db.session.rollback()

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
        db.session.commit()
        # remove manager
        query = select(Node).where(Node.node_name == "manager")
        manager = db.session.execute(query).first()
        if manager:
            db.session.delete(manager[0])
            db.session.commit()
        # remove stacks
        for stack in db.session.scalars(select(InfraStack)):
            db.session.delete(stack)
        db.session.commit()

    def test_remove_devices(self, *args):
        """
        Test tear down of devices
        """
        # setup base stack
        config_base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/base_infra_mock.yml')
        create_infrastack(db.session, config_base)

        # setup agents
        config_agent = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'mocks/mock_agents.yml')
        create_agents_from_config_file(db.session, config_agent)

        # remove agent
        config_agent = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'mocks/mock_one_agent.yml')
        remove_devices_from_config_file(db.session, config_agent)

        # check agent-001 was removed but not agent-002
        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-001-AGENT")
        self.assertEqual(db.session.execute(query).one_or_none(), None)
        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-002-AGENT")
        self.assertEqual(db.session.execute(query).one_or_none() is None, False)

        # remove agent-001 and agent-002
        config_agent = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'mocks/mock_agents.yml')
        remove_devices_from_config_file(db.session, config_agent)

        # check agent-002 removed
        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-002-AGENT")
        self.assertEqual(db.session.execute(query).one_or_none(), None)

        # clean up
        self.cleanup()

    def test_remove_attached_agent(self, *args):
        """
        Test tear down of an agent which is attached (with a Kafka producer)
        """
        # setup base stack
        config_base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/base_infra_mock.yml')
        create_infrastack(db.session, config_base)

        # setup agent
        config_agent = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'mocks/mock_one_agent.yml')
        create_agents_from_config_file(db.session, config_agent)

        # add producer container to agent
        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-001-AGENT")
        agent = db.session.execute(query).one()
        agent[0].create_ksqldb_tables = Mock()
        agent[0].attach(cpus=3)

        # remove agent
        remove_devices_from_config_file(db.session, config_agent)

        # check producer and agent removed
        query = select(DockerContainer).where(DockerContainer.name == "test-zaix-001-producer")
        self.assertEqual(db.session.execute(query).one_or_none(), None)
        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-001-AGENT")
        self.assertEqual(db.session.execute(query).one_or_none(), None)

        # clean up
        self.cleanup()

    def test_remove_devices_notifications(self, *args):
        """
        Test user notifications during device removal
        """
        # setup base stack
        config_base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/base_infra_mock.yml')
        create_infrastack(db.session, config_base)

        # setup agent
        config_agent = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'mocks/mock_one_agent.yml')
        create_agents_from_config_file(db.session, config_agent)

        # add producer container to agent
        query = select(Agent).where(Agent.uuid == "TEST-ZAIX-001-AGENT")
        agent = db.session.execute(query).one()
        agent[0].create_ksqldb_tables = Mock()
        agent[0].attach(cpus=3)

        # remove agent
        user_notify.info.reset_mock()
        user_notify.success.reset_mock()
        config_agent = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'mocks/mock_agents.yml')
        remove_devices_from_config_file(db.session, config_agent)

        # check notifications
        calls = user_notify.info.call_args_list
        self.assertEqual(calls[0], call('zaix-001:'))
        self.assertEqual(calls[1], call('zaix-003:'))
        self.assertEqual(calls[2], call('No Agent TEST-ZAIX-002-AGENT defined in OpenFactory'))

        calls = user_notify.success.call_args_list
        self.assertIn(call('Agent TEST-ZAIX-001-AGENT stopped successfully'), calls)
        self.assertIn(call('Container test-zaix-001-producer removed successfully'), calls)
        self.assertIn(call('Agent TEST-ZAIX-001-AGENT removed successfully'), calls)
        self.assertIn(call('Container test-zaix-001-agent removed successfully'), calls)

        # clean up
        self.cleanup()
