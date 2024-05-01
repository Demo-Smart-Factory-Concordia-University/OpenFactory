import os
from unittest import TestCase
from unittest.mock import patch
from sqlalchemy import select

import tests.mocks as mock
from openfactory.ofa.db import db
from openfactory.models.base import Base
from openfactory.models.infrastack import InfraStack
from openfactory.models.nodes import Node
from openfactory.exceptions import OFAConfigurationException
from openfactory.factories import create_infrastack


@patch("docker.DockerClient", return_value=mock.docker_client)
@patch("docker.APIClient", return_value=mock.docker_apiclient)
class Test_create_infrastack(TestCase):
    """
    Unit tests for create_infrastack factory
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

    def cleanup(self, *args):
        """
        Clean up all stacks and nodes
        """
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

    def test_return_stack(self, *args):
        """
        Test if return value correct
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/base_infra_mock.yml')
        ret = create_infrastack(db.session, config_file)

        # check if return value is correct
        query = select(InfraStack).where(InfraStack.stack_name == "test_base_stack")
        stack = db.session.execute(query).first()
        self.assertEqual(stack[0], ret)

        # clean up
        self.cleanup()

    def test_return_no_stack(self, *args):
        """
        Test if return value correct when no stack is defined in config file
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/no_stack_infra_mock.yml')
        ret = create_infrastack(db.session, config_file)

        # check if return value is correct
        self.assertEqual(ret, None)

        # clean up
        self.cleanup()

    def test_setup_no_stack(self, *args):
        """
        Test setup for a config file without stack
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/no_stack_infra_mock.yml')
        create_infrastack(db.session, config_file)

        # check if manager is setup correctly
        query = select(Node).where(Node.node_name == "manager")
        manager = db.session.execute(query).one()
        self.assertEqual(manager[0].network, 'test-net')
        self.assertEqual(manager[0].node_ip, '123.456.7.800')

        # check if nodes are setup correctly
        query = select(Node).where(Node.node_name == "node1")
        node1 = db.session.execute(query).one()
        self.assertEqual(node1[0].network, 'test-net')
        self.assertEqual(node1[0].node_ip, '123.456.7.801')

        query = select(Node).where(Node.node_name == "node2")
        node2 = db.session.execute(query).one()
        self.assertEqual(node2[0].network, 'test-net')
        self.assertEqual(node2[0].node_ip, '123.456.7.802')

        # clean up
        self.cleanup()

    def test_setup_base_stack(self, *args):
        """
        Test setup of a base stack
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/base_infra_mock.yml')
        stack = create_infrastack(db.session, config_file)

        # check if manager is setup correctly
        manager = stack.manager
        self.assertEqual(manager.network, 'test-net')
        self.assertEqual(manager.node_ip, '123.456.7.800')
        self.assertTrue(manager in stack.nodes)

        # check if nodes are setup correctly
        query = select(Node).where(Node.node_name == "node1")
        node1 = db.session.execute(query).one()
        self.assertEqual(node1[0].network, 'test-net')
        self.assertEqual(node1[0].node_ip, '123.456.7.801')
        self.assertTrue(node1[0] in stack.nodes)

        query = select(Node).where(Node.node_name == "node2")
        node2 = db.session.execute(query).one()
        self.assertEqual(node2[0].network, 'test-net')
        self.assertEqual(node2[0].node_ip, '123.456.7.802')
        self.assertTrue(node2[0] in stack.nodes)

        # clean up
        self.cleanup()

    def test_setup_no_nodes_stack(self, *args):
        """
        Test setup of a stack with no nodes except mamanger node
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/no_nodes_stack_mock.yml')
        stack = create_infrastack(db.session, config_file)

        # check if manager is setup correctly
        manager = stack.manager
        self.assertEqual(manager.network, 'test-net')
        self.assertEqual(manager.node_ip, '123.456.7.800')
        self.assertTrue(manager in stack.nodes)

        # clean up
        self.cleanup()

    def test_setup_no_nodes_infa(self, *args):
        """
        Test setup of a infrastructure with no nodes except mamanger node
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/no_nodes_stack_mock.yml')
        create_infrastack(db.session, config_file)

        # check if manager is setup correctly
        query = select(Node).where(Node.node_name == "manager")
        manager = db.session.execute(query).one()
        self.assertEqual(manager[0].network, 'test-net')
        self.assertEqual(manager[0].node_ip, '123.456.7.800')

        # clean up
        self.cleanup()

    def test_extend_stack(self, *args):
        """
        Test extending a stack with nodes
        """
        # setup base stack
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/base_infra_mock.yml')
        stack1 = create_infrastack(db.session, config_file)

        # setup additional stacks
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/extend1_infra_mock.yml')
        create_infrastack(db.session, config_file)
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/extend2_infra_mock.yml')
        create_infrastack(db.session, config_file)
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/add1_infra_mock.yml')
        stack2 = create_infrastack(db.session, config_file)

        # check if new nodes are setup correctly
        query = select(Node).where(Node.node_name == "node3")
        node = db.session.execute(query).first()
        self.assertEqual(node[0].network, 'test-net')
        self.assertEqual(node[0].node_ip, '123.456.7.803')
        self.assertTrue(node[0] in stack1.nodes)

        query = select(Node).where(Node.node_name == "node4")
        node = db.session.execute(query).first()
        self.assertEqual(node[0].network, 'test-net')
        self.assertEqual(node[0].node_ip, '123.456.7.804')
        self.assertTrue(node[0] in stack1.nodes)

        query = select(Node).where(Node.node_name == "node10")
        node = db.session.execute(query).first()
        self.assertEqual(node[0].network, 'test-net')
        self.assertEqual(node[0].node_ip, '123.456.7.810')
        self.assertTrue(node[0] in stack2.nodes)

        # check if conflicting entries are detected
        # conflict in manager node
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/conflict1_infra_mock.yml')
        self.assertRaises(OFAConfigurationException, create_infrastack, db.session, config_file)
        # conflict in network
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/conflict2_infra_mock.yml')
        self.assertRaises(OFAConfigurationException, create_infrastack, db.session, config_file)

        # clean up
        self.cleanup()

    def test_missing_manager(self, *args):
        """
        Test detection of missing manager
        """
        # Attempt to spin up a stack without any manager defined on an empty infrastructure
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/add1_infra_mock.yml')
        self.assertRaises(OFAConfigurationException, create_infrastack, db.session, config_file)
        self.cleanup()

    def test_missing_network(self, *args):
        """
        Test detection of missing network
        """
        # Attempt to spin up a stack with manager defined but no network defined on an empty infrastructure
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/add2_infra_mock.yml')
        self.assertRaises(OFAConfigurationException, create_infrastack, db.session, config_file)
        self.cleanup()
