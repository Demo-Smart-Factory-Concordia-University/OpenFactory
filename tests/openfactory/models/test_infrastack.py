import os
from unittest import TestCase
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from openfactory.exceptions import OFAException
from openfactory.models.base import Base
from openfactory.models.infrastack import InfraStack
from openfactory.models.nodes import Node
from openfactory.models.agents import Agent
import tests.mocks as mock


@patch("docker.DockerClient", return_value=mock.docker_client)
@patch("docker.APIClient", return_value=mock.docker_apiclient)
@patch("openfactory.models.agents.AgentKafkaProducer", return_value=mock.agent_kafka_producer)
class TestInfraStack(TestCase):
    """
    Unit tests for InfraStack model
    """

    @classmethod
    def setUpClass(cls):
        """ setup in memory sqlite db """
        print("Setting up in memory sqlite db")
        cls.db_engine = create_engine('sqlite:///:memory:')
        Base.metadata.drop_all(cls.db_engine)
        Base.metadata.create_all(cls.db_engine)

    @classmethod
    def tearDownClass(cls):
        print("\nTear down in memory sqlite db")
        Base.metadata.drop_all(cls.db_engine)

    @classmethod
    def setUp(self):
        """ Start a new session """
        self.session = Session(self.db_engine)

    @classmethod
    def tearDown(self):
        """ rollback all transactions """
        self.session.rollback()
        self.session.close()

    def setup_nodes(self, *args):
        """
        Setup a manager and a node
        """
        manager = Node(
            node_name='manager',
            node_ip='123.456.7.891',
            network='test-net'
        )
        self.session.add_all([manager])
        self.session.commit()
        node1 = Node(
            node_name='node1',
            node_ip='123.456.7.901'
        )
        node2 = Node(
            node_name='node2',
            node_ip='123.456.7.902'
        )
        self.session.add_all([node1, node2])
        self.session.commit()
        return manager, node1, node2

    def cleanup(self, *args):
        """
        Clean up all nodes and stacks
        """
        # remove nodes
        for node in self.session.scalars(select(Node)):
            if node.node_name != 'manager':
                self.session.delete(node)
        # remove manager
        query = select(Node).where(Node.node_name == "manager")
        manager = self.session.execute(query).first()
        if manager:
            self.session.delete(manager[0])
        self.session.commit()
        # remove stacks
        for stack in self.session.scalars(select(InfraStack)):
            self.session.delete(stack)
        self.session.commit()

    def test_class_parent(self, *args):
        """
        Test parent of class is Base
        """
        self.assertEqual(InfraStack.__bases__[0], Base)

    def test_table_name(self, *args):
        """
        Test table name
        """
        self.assertEqual(InfraStack.__tablename__, 'ofa_infra_stack')

    def test_infrastack_setup(self, *args):
        """
        Test setup and tear down of a InfraStack
        """
        inrastack = InfraStack(stack_name='Test Stack')
        self.session.add_all([inrastack])
        self.session.commit()

        query = select(InfraStack).where(InfraStack.stack_name == "Test Stack")
        stack = self.session.execute(query).first()
        self.assertEqual(stack[0].stack_name, 'Test Stack')

        # clean up
        self.cleanup()

    def test_stack_name_unique(self, *args):
        """
        Test InfraStack.stack_name is required to be unique
        """
        inrastack1 = InfraStack(stack_name='Test Stack')
        inrastack2 = InfraStack(stack_name='Test Stack')
        self.session.add_all([inrastack1, inrastack2])
        self.assertRaises(IntegrityError, self.session.commit)

    def test_teardown_infrastack(self, *args):
        """
        Test tear down of an InfraStack
        """
        # setup a stack
        manager_node, node1, node2 = self.setup_nodes()
        inrastack = InfraStack(stack_name='Test Stack',
                               nodes=[manager_node, node1])
        self.session.add_all([inrastack])
        self.session.commit()

        # check stack cannot be removed if nodes are still present
        self.session.delete(inrastack)
        self.assertRaises(OFAException, self.session.commit)
        self.session.rollback()

        # check nodes are still present
        query = select(Node).where(Node.node_name == "manager")
        manager = self.session.execute(query).first()
        self.assertEqual(manager[0], manager_node)
        query = select(Node).where(Node.node_name == "node1")
        manager = self.session.execute(query).first()
        self.assertEqual(manager[0], node1)

        # check stack can be removed if no nodes are present
        self.session.delete(node1)
        self.session.delete(node2)
        self.session.commit()
        self.session.delete(manager_node)
        self.session.commit()
        self.session.delete(inrastack)
        self.session.commit()

        # clean up
        self.cleanup()

    def test_manager(self, *args):
        """
        Test hybride property 'manager' of an InfraStack
        """
        inrastack = InfraStack(stack_name='Test Stack')
        self.session.add_all([inrastack])
        self.session.commit()

        # test manger is None if stack is empty
        self.assertEqual(inrastack.manager, None)

        manager, node1, node2 = self.setup_nodes()
        inrastack.nodes.append(manager)
        inrastack.nodes.append(node1)
        self.session.commit()

        # test manager is set correcty if nodes are in stack
        self.assertEqual(inrastack.manager, manager)

        # clean up
        self.cleanup()

    def test_clear(self, *args):
        """
        Test clear stack
        """
        # setup a stack
        manager, node1, node2 = self.setup_nodes()
        agent = Agent(uuid='TEST-AGENT',
                      node=node1,
                      agent_port=5000)
        self.session.add_all([agent])
        self.session.commit()
        device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/mock_device.xml')
        agent.create_container('123.456.7.500', 7878, device_file, 1)

        inrastack = InfraStack(stack_name='Test Stack',
                               nodes=[manager, node1])
        self.session.add_all([inrastack])
        self.session.commit()

        # clear stack
        inrastack.clear()

        # test mananger and node1 not removed
        query = select(Node).where(Node.node_name == "manager")
        res = self.session.execute(query).one()
        self.assertEqual(res[0], manager)
        query = select(Node).where(Node.node_name == "node1")
        res = self.session.execute(query).one()
        self.assertEqual(res[0], node1)

        # remove agent and clear stack again
        self.session.delete(agent)
        self.session.commit()
        inrastack.clear()

        # test mananger not removed and node1 removed
        query = select(Node).where(Node.node_name == "manager")
        res = self.session.execute(query).one()
        self.assertEqual(res[0], manager)
        query = select(Node).where(Node.node_name == "node1")
        self.assertEqual(self.session.execute(query).one_or_none(), None)

        # remove node2 and clear stack again
        self.session.delete(node2)
        self.session.commit()
        inrastack.clear()

        # test mananger removed
        query = select(Node).where(Node.node_name == "manager")
        self.assertEqual(self.session.execute(query).one_or_none(), None)

        # clean up
        self.cleanup()
