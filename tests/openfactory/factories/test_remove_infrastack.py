import os
from unittest import TestCase
from unittest.mock import patch
from sqlalchemy import select

import tests.mocks as mock
import openfactory.ofa as ofa
from openfactory.ofa.db import db
from openfactory.factories import create_infrastack
from openfactory.models.base import Base
from openfactory.models.infrastack import InfraStack
from openfactory.models.nodes import Node


@patch("docker.DockerClient", return_value=mock.docker_client)
@patch("docker.APIClient", return_value=mock.docker_apiclient)
class Test_remove_infrastack(TestCase):
    """
    Unit tests for remove_infrastack
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

    def test_down_single_stack(self, *args):
        """
        Test tear down of a single stack
        """
        # setup base stack
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/base_infra_mock.yml')
        create_infrastack(db.session, config_file)

        # remove stack
        ofa.stack.down(db.session, config_file)

        # check stack and nodes were removed
        self.assertEqual(len(db.session.query(InfraStack).all()), 0)
        self.assertEqual(len(db.session.query(Node).all()), 0)

        # clean up
        self.cleanup()

    def test_down_additional_stack(self, *args):
        """
        Test tear down of a stack among several stacks
        """
        # setup base stack
        config_base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/base_infra_mock.yml')
        create_infrastack(db.session, config_base)

        # setup additional stack
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/add1_infra_mock.yml')
        create_infrastack(db.session, config_file)

        # remove additional stack
        ofa.stack.down(db.session, config_file)

        # check stack and nodes were removed
        query = select(InfraStack).where(InfraStack.stack_name == "test_add_stack")
        self.assertEqual(db.session.execute(query).one_or_none(), None)
        query = select(Node).where(Node.node_name == "node10")
        self.assertEqual(db.session.execute(query).one_or_none(), None)

        # check remaining stacks and nodes were not removed
        query = select(InfraStack).where(InfraStack.stack_name == "test_base_stack")
        self.assertEqual(len(db.session.execute(query).one()), 1)
        query = select(Node).where(Node.node_name == "manager")
        self.assertEqual(len(db.session.execute(query).one()), 1)
        query = select(Node).where(Node.node_name == "node1")
        self.assertEqual(len(db.session.execute(query).one()), 1)
        query = select(Node).where(Node.node_name == "node2")
        self.assertEqual(len(db.session.execute(query).one()), 1)

        # setup additional stack
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/add1_infra_mock.yml')
        create_infrastack(db.session, config_file)

        # check base stack cannot be removed
        ofa.stack.down(db.session, config_base)
        query = select(InfraStack).where(InfraStack.stack_name == "test_base_stack")
        self.assertEqual(len(db.session.execute(query).one()), 1)
        query = select(Node).where(Node.node_name == "manager")
        self.assertEqual(len(db.session.execute(query).one()), 1)

        # check nodes from base stack were removed
        query = select(Node).where(Node.node_name == "node1")
        self.assertEqual(db.session.execute(query).one_or_none(), None)
        query = select(Node).where(Node.node_name == "node2")
        self.assertEqual(db.session.execute(query).one_or_none(), None)

        # clean up
        self.cleanup()

    def test_down_manager(self, *args):
        """
        Test stack tear down does not remove manager if other nodes still exist
        """
        # setup stacks
        config_file1 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'mocks/infra/base_infra_mock.yml')
        create_infrastack(db.session, config_file1)

        # setup additional stack
        config_file2 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'mocks/infra/add2_infra_mock.yml')
        create_infrastack(db.session, config_file2)

        # remove stack
        ofa.stack.down(db.session, config_file1)

        # check nodes were removed
        query = select(Node).where(Node.node_name == "node1")
        self.assertEqual(db.session.execute(query).one_or_none(), None)
        query = select(Node).where(Node.node_name == "node2")
        self.assertEqual(db.session.execute(query).one_or_none(), None)

        # check manager was not removed
        query = select(Node).where(Node.node_name == "manager")
        self.assertEqual(len(db.session.execute(query).one()), 1)

        # check stack was not removed
        query = select(InfraStack).where(InfraStack.stack_name == "test_base_stack")
        self.assertEqual(len(db.session.execute(query).one()), 1)

        # clean up
        self.cleanup()
