import unittest
from unittest.mock import patch, MagicMock
from docker.errors import APIError
from openfactory.factories.remove_infra import remove_workers


class TestRemoveWorkers(unittest.TestCase):
    """
    Test remove_workers
    """

    @patch('openfactory.factories.remove_infra.config')
    @patch('openfactory.factories.remove_infra.user_notify')
    @patch('openfactory.factories.remove_infra.docker.DockerClient')
    @patch('openfactory.factories.remove_infra.dal')
    def test_remove_workers_success(
        self, mock_dal, mock_docker_client, mock_user_notify, mock_config
    ):
        # Setup
        mock_config.OPENFACTORY_USER = 'testuser'

        workers = {
            'worker1': {'ip': '192.168.1.10'},
        }
        node_ip_map = {
            '192.168.1.10': 'node_id_1',
        }

        # Mock node object and methods
        mock_node = MagicMock()
        mock_node.attrs = {'Spec': {'Availability': 'active'}}
        mock_dal.docker_client.nodes.get.return_value = mock_node

        # Mock SSH Docker client
        mock_ssh_client = MagicMock()
        mock_docker_client.return_value = mock_ssh_client

        # Call function
        remove_workers(workers, node_ip_map)

        # Assertions

        # correct node draining
        mock_user_notify.info.assert_any_call('Draining node worker1 ...')
        mock_node.update.assert_called_once()
        args, kwargs = mock_node.update.call_args
        self.assertIn('Availability', args[0])
        self.assertEqual(args[0]['Availability'], 'drain')

        # leaving swarm on worker node
        mock_docker_client.assert_called_once_with(base_url='ssh://testuser@192.168.1.10')
        mock_ssh_client.swarm.leave.assert_called_once()

        # remove node from manager node
        mock_dal.docker_client.api.remove_node.assert_called_with('node_id_1', force=True)
        mock_user_notify.success.assert_called_with('Removed node worker1')

    @patch('openfactory.factories.remove_infra.config')
    @patch('openfactory.factories.remove_infra.user_notify')
    @patch('openfactory.factories.remove_infra.docker.DockerClient')
    @patch('openfactory.factories.remove_infra.dal')
    def test_remove_workers_missing_ip(
        self, mock_dal, mock_docker_client, mock_user_notify, mock_config
    ):
        """ Test case of missing IP in node_ip_map """
        # IP not in node_ip_map
        workers = {
            'worker1': {'ip': '192.168.1.10'},
        }
        node_ip_map = {
            '192.168.1.99': 'node_id_1',
        }

        remove_workers(workers, node_ip_map)

        # Should not call anything since IP is not found
        mock_user_notify.info.assert_not_called()
        mock_user_notify.success.assert_not_called()

    @patch('openfactory.factories.remove_infra.config')
    @patch('openfactory.factories.remove_infra.user_notify')
    @patch('openfactory.factories.remove_infra.docker.DockerClient')
    @patch('openfactory.factories.remove_infra.dal')
    def test_remove_workers_api_error(
        self, mock_dal, mock_docker_client, mock_user_notify, mock_config
    ):
        """ Test if APIError is handled """
        mock_config.OPENFACTORY_USER = 'testuser'

        workers = {
            'worker1': {'ip': '192.168.1.10'},
        }
        node_ip_map = {
            '192.168.1.10': 'node_id_1',
        }

        # Simulate an API error
        mock_dal.docker_client.nodes.get.side_effect = APIError("API Error")

        remove_workers(workers, node_ip_map)

        mock_user_notify.fail.assert_called()
        self.assertIn('Node "worker1" could not be removed', mock_user_notify.fail.call_args[0][0])
