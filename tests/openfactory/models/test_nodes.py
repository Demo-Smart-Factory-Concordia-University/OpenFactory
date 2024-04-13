from unittest import TestCase
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import tests.mocks as mock
import openfactory.config as config
from openfactory.models.base import Base
from openfactory.models.nodes import Node


@patch("docker.DockerClient", return_value=mock.docker_client)
@patch("docker.APIClient", return_value=mock.docker_apiclient)
class TestNodes(TestCase):
    """
    Unit tests for Nodes model
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
        """ Close session """
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
        node = Node(
            node_name='node',
            node_ip='123.456.7.901'
        )
        self.session.add_all([node])
        self.session.commit()
        return manager, node

    def cleanup(self, *args):
        """
        Clean up all nodes
        """
        self.session.rollback()
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

    def test_class_parent(self, *args):
        """
        Test parent of class is Base
        """
        self.assertEqual(Node.__bases__[0], Base)

    def test_table_name(self, *args):
        """
        Test table name
        """
        self.assertEqual(Node.__tablename__, 'ofa_nodes')

    def test_manager_setup(self, mock_DockerAPIClient, mock_DockerClient):
        """
        Test setup and tear down of a manager node
        """
        # reset mocks
        mock_DockerClient.reset_mock()
        mock.docker_client.reset_mock()

        # setup manager node
        node = Node(
            node_name='manager',
            node_ip='123.456.7.891',
            network='test-net'
        )
        self.session.add_all([node])
        self.session.commit()

        # use correct docker client
        mock_DockerClient.assert_called_once_with(base_url='ssh://' + config.OPENFACTORY_USER + '@123.456.7.891')
        mock.docker_client.close.assert_called_once()

        # setup correctly manager node
        args, kwargs = mock.docker_swarm.init.call_args
        self.assertEqual(kwargs['advertise_addr'], '123.456.7.891')

        # setup correctly network
        args, kwargs = mock.docker_networks.create.call_args
        self.assertEqual(args[0], 'test-net')
        self.assertEqual(kwargs['driver'], 'overlay')
        self.assertEqual(kwargs['attachable'], True)

        # entry in database is correct
        query = select(Node).where(Node.node_name == "manager")
        manager = self.session.execute(query).first()
        self.assertEqual(manager[0].node_name, 'manager')
        self.assertEqual(manager[0].network, 'test-net')
        self.assertEqual(manager[0].node_ip, '123.456.7.891')
        self.assertEqual(manager[0].cpus, 5)
        self.assertEqual(manager[0].memory, 1)
        self.assertEqual(manager[0].docker_node_id, 'swarm_node_id')
        self.assertEqual(manager[0].docker_url, 'ssh://' + config.OPENFACTORY_USER + '@123.456.7.891')
        self.assertEqual(manager[0].manager, manager[0])

        # tear down manager node
        self.session.delete(manager[0])
        self.session.commit()

        # use correct docker client
        mock_DockerClient.assert_called_with(base_url='ssh://' + config.OPENFACTORY_USER + '@123.456.7.891')
        mock.docker_client.close.assert_called()

        # manager node removed correctly
        args, kwargs = mock.docker_swarm.leave.call_args
        self.assertEqual(kwargs['force'], True)

    def test_node_setup(self, mock_DockerAPIClient, mock_DockerClient):
        """
        Test setup and tear down of an OpenFactory node
        """
        self.setup_nodes()

        # entry in database is correct
        query = select(Node).where(Node.node_name == "manager")
        manager = self.session.execute(query).first()
        query = select(Node).where(Node.node_name == "node")
        n = self.session.execute(query).first()
        self.assertEqual(n[0].node_name, 'node')
        self.assertEqual(n[0].network, 'test-net')
        self.assertEqual(n[0].node_ip, '123.456.7.901')
        self.assertEqual(n[0].cpus, 5)
        self.assertEqual(n[0].memory, 1)
        self.assertEqual(n[0].docker_node_id, 'a node id')
        self.assertEqual(n[0].docker_url, 'ssh://' + config.OPENFACTORY_USER + '@123.456.7.901')
        self.assertEqual(n[0].manager, manager[0])

        self.session.delete(n[0])
        self.session.commit()

        # use correct docker client
        mock_DockerClient.assert_called_with(base_url='ssh://' + config.OPENFACTORY_USER + '@123.456.7.901')
        mock.docker_client.close.assert_called()

        # leave swarm
        mock.docker_swarm.leave.assert_called()

        # remove node from swarm manager
        mock_DockerAPIClient.assert_called_with('ssh://' + config.OPENFACTORY_USER + '@123.456.7.891')
        args, kwargs = mock.docker_apiclient.remove_node.call_args
        self.assertEqual(args[0], 'a node id')
        self.assertEqual(kwargs['force'], True)

        # clean-up
        self.cleanup()

    def test_node_name_unique(self, *args):
        """
        Test Node.node_name is required to be unique
        """
        self.setup_nodes()
        node2 = Node(
            node_name='node',
            node_ip='123.456.7.902'
        )
        self.session.add_all([node2])
        self.assertRaises(IntegrityError, self.session.commit)

        # clean-up
        self.cleanup()

    def test_node_ip_unique(self, *args):
        """
        Test Node.node_ip is required to be unique
        """
        self.setup_nodes()
        node2 = Node(
            node_name='node2',
            node_ip='123.456.7.901'
        )
        self.session.add_all([node2])
        self.assertRaises(IntegrityError, self.session.commit)

        # clean-up
        self.cleanup()

    def test_node_status(self, *args):
        """
        Test hybride property 'status' of an OpenFactory node
        """
        manager, node = self.setup_nodes()

        self.assertEqual(node.status, 'ready')

        # clean-up
        self.cleanup()
