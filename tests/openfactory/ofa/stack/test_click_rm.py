import os
from unittest import TestCase
from unittest.mock import patch
from click.testing import CliRunner
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
class Test_ofa_stack_click_rm(TestCase):
    """
    Unit tests for ofa.stack.click_rm function
    """

    @classmethod
    def setUpClass(cls):
        """ setup in memory sqlite db """
        db.conn_uri = 'sqlite:///:memory:'
        db.connect()
        Base.metadata.create_all(db.engine)

    @classmethod
    def tearDownClass(cls):
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

    def test_rm_single_stack(self, *args):
        """
        Test tear down of a single stack
        """
        runner = CliRunner()

        # setup base stack
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/base_infra_mock.yml')
        stack = create_infrastack(db.session, config_file)

        # remove stack
        result = runner.invoke(ofa.stack.click_rm, [stack.stack_name])

        # check no error
        self.assertEqual(result.exit_code, 0)

        # check stack and nodes were removed
        self.assertEqual(len(db.session.query(InfraStack).all()), 0)
        self.assertEqual(len(db.session.query(Node).all()), 0)

        # clean up
        self.cleanup()

    def test_rm_additional_stack(self, *args):
        """
        Test tear down of a stack among several stacks
        """
        runner = CliRunner()

        # setup base stack
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/base_infra_mock.yml')
        create_infrastack(db.session, config_file)

        # setup additional stack
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/add1_infra_mock.yml')
        stack2 = create_infrastack(db.session, config_file)

        # remove additional stack
        result = runner.invoke(ofa.stack.click_rm, [stack2.stack_name])

        # check no error
        self.assertEqual(result.exit_code, 0)

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

        # clean up
        self.cleanup()

    def test_rm_manager(self, *args):
        """
        Test tear down of a stack does not remove manager if other nodes still exist
        """
        runner = CliRunner()

        # setup stacks
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/base_infra_mock.yml')
        stack1 = create_infrastack(db.session, config_file)

        # setup additional stack
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mock/infra/add2_infra_mock.yml')
        create_infrastack(db.session, config_file)

        # remove stack
        result = runner.invoke(ofa.stack.click_rm, [stack1.stack_name])
        print(result.output)

        # check no error
        self.assertEqual(result.exit_code, 0)

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
