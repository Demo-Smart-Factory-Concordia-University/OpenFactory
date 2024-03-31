import os
from unittest import TestCase
from unittest.mock import patch
from sqlalchemy import select

import tests.mocks as mock
import openfactory.ofa as ofa
from openfactory.ofa.db import db
from openfactory.models.base import Base
from openfactory.models.infrastack import InfraStack
from openfactory.models.nodes import Node
from openfactory.exceptions import OFAConfigurationException


@patch("docker.DockerClient", return_value=mock.docker_client)
@patch("docker.APIClient", return_value=mock.docker_apiclient)
class Test_ofa_stack_up(TestCase):
    """
    Unit tests for ofa.stack.up function
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
        for stack in db.session.scalars(select(InfraStack)):
            # remove nodes
            for node in stack.nodes:
                if node.node_name != 'manager':
                    db.session.delete(node)
            db.session.delete(stack)
            db.session.commit()
        # remove manager
        query = select(Node).where(Node.node_name == "manager")
        manager = db.session.execute(query).first()
        if manager:
            db.session.delete(manager[0])
            db.session.commit()

    def test_setup_base_stack(self, *args):
        """
        Test setup of a base stack
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/base_infra_mock.yml')
        ofa.stack.up(db.session, config_file)

        # check if InfraStack is setup correctly
        query = select(InfraStack).where(InfraStack.stack_name == "test_base_stack")
        stack = db.session.execute(query).first()
        self.assertEqual(stack[0].stack_name, 'test_base_stack')

        # check if manager is setup correctly
        manager = stack[0].manager
        self.assertEqual(manager.network, 'test-net')
        self.assertEqual(manager.node_ip, '123.456.7.800')
        self.assertTrue(manager in stack[0].nodes)

        # check if nodes are setup correctly
        query = select(Node).where(Node.node_name == "node1")
        node1 = db.session.execute(query).first()
        self.assertEqual(node1[0].network, 'test-net')
        self.assertEqual(node1[0].node_ip, '123.456.7.801')
        self.assertTrue(node1[0] in stack[0].nodes)

        query = select(Node).where(Node.node_name == "node2")
        node2 = db.session.execute(query).first()
        self.assertEqual(node2[0].network, 'test-net')
        self.assertEqual(node2[0].node_ip, '123.456.7.802')
        self.assertTrue(node2[0] in stack[0].nodes)

        # clean up
        self.cleanup()

    def test_extend_stack(self, *args):
        """
        Test extending a stack with nodes
        """
        # setup base stack
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/base_infra_mock.yml')
        ofa.stack.up(db.session, config_file)
        query = select(InfraStack).where(InfraStack.stack_name == "test_base_stack")
        stack = db.session.execute(query).first()
        stack1 = stack[0]

        # setup additional stacks
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/extend1_infra_mock.yml')
        ofa.stack.up(db.session, config_file)
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/extend2_infra_mock.yml')
        ofa.stack.up(db.session, config_file)
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/add1_infra_mock.yml')
        ofa.stack.up(db.session, config_file)
        query = select(InfraStack).where(InfraStack.stack_name == "test_add_stack")
        stack = db.session.execute(query).first()
        stack2 = stack[0]

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
                                   'mock/infra/conflict1_infra_mock.yml')
        self.assertRaises(OFAConfigurationException, ofa.stack.up, db.session, config_file)
        # conflict in network
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/conflict2_infra_mock.yml')
        self.assertRaises(OFAConfigurationException, ofa.stack.up, db.session, config_file)

        # clean up
        self.cleanup()

    def test_missing_manager(self, *args):
        """
        Test detection of missing manager
        """
        # Attempt to spin up a stack without any manager defined on an empty infrastructure
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/add1_infra_mock.yml')
        self.assertRaises(OFAConfigurationException, ofa.stack.up, db.session, config_file)
        self.cleanup()

    def test_missing_network(self, *args):
        """
        Test detection of missing network
        """
        # Attempt to spin up a stack with manager defined but no network defined on an empty infrastructure
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/add2_infra_mock.yml')
        self.assertRaises(OFAConfigurationException, ofa.stack.up, db.session, config_file)
        self.cleanup()
