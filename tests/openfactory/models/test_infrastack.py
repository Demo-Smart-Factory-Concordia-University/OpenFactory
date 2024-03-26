from unittest import TestCase
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from openfactory.models.base import Base
from openfactory.models.infrastack import InfraStack
from openfactory.models.nodes import Node
import tests.mocks as mock


@patch("docker.DockerClient", return_value=mock.docker_client)
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

        self.session.delete(stack[0])
        self.session.commit()

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
        inrastack = InfraStack(stack_name='Test Stack')
        self.session.add_all([inrastack])
        self.session.commit()
        manager_node = Node(
            node_name='manager',
            node_ip='123.456.7.891',
            network='test-net'
        )
        inrastack.nodes.append(manager_node)
        self.session.add_all([manager_node])
        self.session.commit()

        # teardown stack
        self.session.delete(inrastack)
        self.session.commit()

        # check nodes are still present
        query = select(Node).where(Node.node_name == "manager")
        manager = self.session.execute(query).first()
        self.assertEqual(manager[0], manager_node)

        # clean-up
        self.session.delete(manager_node)
        self.session.commit()

    def test_manager(self, *args):
        """
        Test hybride property 'manager' of an InfraStack
        """
        inrastack = InfraStack(stack_name='Test Stack')
        self.session.add_all([inrastack])
        self.session.commit()

        # test manger is None if stack is empty
        self.assertEqual(inrastack.manager, None)

        manager_node = Node(
            node_name='manager',
            node_ip='123.456.7.891',
            network='test-net'
        )
        inrastack.nodes.append(manager_node)
        self.session.add_all([manager_node])
        self.session.commit()

        # test manager is set correcty if nodes are in stack
        self.assertEqual(inrastack.manager, manager_node)

        # clean-up
        self.session.delete(inrastack)
        self.session.delete(manager_node)
        self.session.commit()
