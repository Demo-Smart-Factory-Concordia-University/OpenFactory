import unittest
from unittest.mock import patch, MagicMock
from openfactory.docker.docker_access_layer import DockerAccesLayer
from openfactory.exceptions import OFAException


class TestDockerAccessLayer(unittest.TestCase):
    """
    Test cases for DockerAccesLayer class
    """

    @patch('openfactory.docker.docker_access_layer.config')
    @patch('openfactory.docker.docker_access_layer.docker.DockerClient')
    def test_connect_success(self, mock_docker_client, mock_config):
        """ Test successful connection to Docker engine in Swarm mode """
        mock_config.OPENFACTORY_MANAGER_NODE_DOCKER_URL = 'tcp://127.0.0.1:2375'
        mock_config.OPENFACTORY_MANAGER_NODE = '127.0.0.1'
        mock_swarm_attrs = {
            'JoinTokens': {
                'Worker': 'worker-token',
                'Manager': 'manager-token'
            }
        }
        mock_docker_client.return_value.swarm.attrs = mock_swarm_attrs

        dal = DockerAccesLayer()
        dal.connect()

        self.assertEqual(dal.docker_url, 'tcp://127.0.0.1:2375')
        self.assertEqual(dal.ip, '127.0.0.1')
        self.assertEqual(dal.worker_token, 'worker-token')
        self.assertEqual(dal.manager_token, 'manager-token')

    @patch('openfactory.docker.docker_access_layer.config')
    @patch('openfactory.docker.docker_access_layer.docker.DockerClient')
    def test_connect_swarm_mode_exception(self, mock_docker_client, mock_config):
        """ Test connection to Docker engine in Swarm mode with exception """
        mock_config.OPENFACTORY_MANAGER_NODE_DOCKER_URL = 'tcp://127.0.0.1:2375'
        mock_docker_client.return_value.swarm.attrs = {}

        dal = DockerAccesLayer()
        with self.assertRaises(OFAException) as context:
            dal.connect()

        self.assertIn('Docker running on tcp://127.0.0.1:2375 is not in Swarm mode', str(context.exception))

    @patch('openfactory.docker.docker_access_layer.docker.DockerClient')
    def test_get_node_name_labels(self, mock_docker_client):
        """ Test getting node name labels """
        mock_nodes = [
            MagicMock(attrs={'Spec': {'Labels': {'name': 'node1'}}}),
            MagicMock(attrs={'Spec': {'Labels': {'name': 'node2'}}}),
            MagicMock(attrs={'Spec': {'Labels': {}}}),
        ]
        mock_docker_client.return_value.nodes.list.return_value = mock_nodes

        dal = DockerAccesLayer()
        dal.docker_client = mock_docker_client.return_value
        name_labels = dal.get_node_name_labels()

        self.assertEqual(name_labels, ['node1', 'node2'])

    @patch('openfactory.docker.docker_access_layer.docker.DockerClient')
    def test_get_node_ip_addresses(self, mock_docker_client):
        """ Test getting node IP addresses """
        mock_nodes = [
            MagicMock(attrs={'Status': {'Addr': '192.168.1.1'}}),
            MagicMock(attrs={'Status': {'Addr': '192.168.1.2'}}),
            MagicMock(attrs={'Status': {}}),
        ]
        mock_docker_client.return_value.nodes.list.return_value = mock_nodes

        dal = DockerAccesLayer()
        dal.docker_client = mock_docker_client.return_value
        ip_addresses = dal.get_node_ip_addresses()

        self.assertEqual(ip_addresses, ['192.168.1.1', '192.168.1.2'])
