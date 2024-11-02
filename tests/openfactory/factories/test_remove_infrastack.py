import os
from unittest import TestCase
from unittest.mock import patch, Mock

import tests.mocks as mock
from openfactory.docker.docker_access_layer import dal
from openfactory.factories import remove_infrastack


# Mock a node
mock_node = Mock()
mock_node.id = 'mock_id'
mock_node.attrs = {
    'Status': {'Addr': '192.168.123.111'},
    'Spec': {'Labels': {}}
}
mock_node.update = Mock()


def mock_nodes_get(node_id):
    if node_id == 'mock_id':
        return mock_node
    else:
        return None


@patch("docker.APIClient", return_value=mock.docker_apiclient)
@patch("docker.DockerClient", return_value=mock.docker_client)
class Test_remove_infrastack(TestCase):
    """
    Unit tests for remove_infrastack
    """

    @classmethod
    def setUpClass(cls):
        dal.docker_client = mock.docker_client
        dal.docker_client.nodes.list = Mock(return_value=[mock_node])
        dal.docker_client.nodes.get = Mock(return_value=mock_node)
        dal.docker_client.api.remove_node = Mock()

    @patch("openfactory.factories.remove_infra.config")
    def test_remove_infrastack(self, mock_config, mock_docker_client, *args):
        """
        Test tear down of a single stack
        """
        mock_config.OPENFACTORY_USER = 'mock_user'

        # remove stack
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/single_mock.yml')
        remove_infrastack(config_file)

        # check if node gets drained
        mock_node.update.assert_called_once()
        call_args, _ = mock_node.update.call_args
        self.assertEqual(call_args[0]['Availability'], 'drain')

        # remove node on manager node
        dal.docker_client.api.remove_node.assert_called_once_with('mock_id', force=True)

        # leave swarm cluster on node to be removed
        mock_docker_client.assert_called_once_with(base_url='ssh://mock_user@192.168.123.111')
        mock.docker_client.swarm.leave.assert_called_once_with()
