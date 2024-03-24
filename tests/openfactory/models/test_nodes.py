from unittest import TestCase
from unittest.mock import patch
from unittest.mock import Mock, PropertyMock
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session

import openfactory.config as config
from openfactory.models.base import Base
from openfactory.models.nodes import Node


"""
Mock Python Docker SDK Swarm object
"""
mock_docker_swarm = Mock()
mock_docker_swarm.attrs = {
    'JoinTokens': {'Worker': 'docker_swarm_manager_token'}
}
mock_docker_swarm.init = Mock(return_value='swarm_node_id')
mock_docker_swarm.leave = Mock()


"""
Mock Python Docker SDK Node object
"""
mock_docker_node = Mock()
mock_docker_node.attrs = {
    'Status': {'State': 'ready', 'Addr': '123.456.7.900'}
}


"""
Mock Python Docker SDK Nodes object
"""
mock_docker_nodes = Mock()
mock_docker_nodes.get = Mock(return_value=mock_docker_node)


"""
Mock Python Docker SDK Network object
"""
mock_docker_network = Mock()
mock_docker_network.create = Mock(return_value='docker_network')


"""
Mock return value of DockerClient.info()
"""
INFO_DIC = {
    'Swarm': {'NodeID': 'a node id'},
    'NCPU': 5,
    'MemTotal': 1073741824
}


@patch("docker.APIClient.__init__", return_value=None)
@patch("docker.APIClient.remove_node")
@patch("docker.APIClient.close")
@patch("docker.DockerClient.__init__", return_value=None)
@patch("docker.DockerClient.info", return_value=INFO_DIC)
@patch("docker.DockerClient.nodes", new_callable=PropertyMock, return_value=mock_docker_nodes)
@patch("docker.DockerClient.close")
@patch("docker.DockerClient.networks", new_callable=PropertyMock, return_value=mock_docker_network)
@patch("docker.DockerClient.swarm", new_callable=PropertyMock, return_value=mock_docker_swarm)
class TestNodes(TestCase):
    """
    Unit tests for Nodes model
    """

    @classmethod
    def setUpClass(cls):
        """ setup in memory sqlite db """
        print("Setting up in memory sqlite db")
        cls.db_engine = create_engine('sqlite:///:memory')
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

    def test_manager_setup(self,
                           mock_swarm,
                           mock_network,
                           mock_DockerClientClose,
                           mock_DockerClientNodes,
                           mock_DockerClientInfo,
                           mock_DockerClient,
                           mock_DockerAPIClientClose,
                           mock_DockerRemove_node,
                           mock_DockerAPIClient):
        """
        Test setup and tear down of a manager node
        """
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
        mock_DockerClientClose.assert_called_once()

        # setup correctly manager node
        args, kwargs = mock_docker_swarm.init.call_args
        self.assertEqual(kwargs['advertise_addr'], '123.456.7.891')

        # setup correctly network
        args, kwargs = mock_docker_network.create.call_args
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
        self.session.delete(node)
        self.session.commit()

        # use correct docker client
        mock_DockerClient.assert_called_with(base_url='ssh://' + config.OPENFACTORY_USER + '@123.456.7.891')
        mock_DockerClientClose.assert_called()

        # manager node removed correctly
        args, kwargs = mock_docker_swarm.leave.call_args
        self.assertEqual(kwargs['force'], True)

    def test_node_setup(self,
                        mock_swarm,
                        mock_docker_network,
                        mock_DockerClientClose,
                        mock_DockerClientNodes,
                        mock_DockerClientInfo,
                        mock_DockerClient,
                        mock_DockerAPIClientClose,
                        mock_DockerRemove_node,
                        mock_DockerAPIClient):
        """
        Test setup of an OpenFactory node
        """
        manager_node = Node(
            node_name='manager',
            node_ip='123.456.7.891',
            network='test-net'
        )
        node = Node(
            node_name='node1',
            node_ip='123.456.7.901'
        )

        self.session.add_all([manager_node])
        self.session.commit()
        self.session.add_all([node])
        self.session.commit()

        # entry in database is correct
        query = select(Node).where(Node.node_name == "manager")
        manager = self.session.execute(query).first()
        query = select(Node).where(Node.node_name == "node1")
        n = self.session.execute(query).first()
        self.assertEqual(n[0].node_name, 'node1')
        self.assertEqual(n[0].network, 'test-net')
        self.assertEqual(n[0].node_ip, '123.456.7.901')
        self.assertEqual(n[0].cpus, 5)
        self.assertEqual(n[0].memory, 1)
        self.assertEqual(n[0].docker_node_id, 'a node id')
        self.assertEqual(n[0].docker_url, 'ssh://' + config.OPENFACTORY_USER + '@123.456.7.901')
        self.assertEqual(n[0].manager, manager[0])

        self.session.delete(node)
        self.session.commit()

        # use correct docker client
        mock_DockerClient.assert_called_with(base_url='ssh://' + config.OPENFACTORY_USER + '@123.456.7.901')
        mock_DockerClientClose.assert_called()

        # leave swarm
        mock_docker_swarm.leave.assert_called()

        # remove node from swarm manager
        mock_DockerAPIClient.assert_called_with('ssh://' + config.OPENFACTORY_USER + '@123.456.7.891')
        args, kwargs = mock_DockerRemove_node.call_args
        self.assertEqual(args[0], 'a node id')
        self.assertEqual(kwargs['force'], True)

        self.session.delete(manager_node)
        self.session.commit()

    def test_node_status(self,
                         mock_swarm,
                         mock_docker_network,
                         mock_DockerClientClose,
                         mock_DockerClientNodes,
                         mock_DockerClientInfo,
                         mock_DockerClient,
                         mock_DockerAPIClientClose,
                         mock_DockerRemove_node,
                         mock_DockerAPIClient):
        """
        Test status hybride property of an OpenFactory node
        """
        manager_node = Node(
            node_name='manager',
            node_ip='123.456.7.891',
            network='test-net'
        )

        node = Node(
            node_name='node2',
            node_ip='123.456.7.902'
        )

        self.session.add_all([manager_node])
        self.session.commit()
        self.session.add_all([node])
        self.session.commit()

        self.assertEqual(node.status, 'ready')

        self.session.delete(node)
        self.session.commit()
        self.session.delete(manager_node)
        self.session.commit()
