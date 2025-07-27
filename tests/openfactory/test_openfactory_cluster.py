from unittest import TestCase
from unittest.mock import patch, Mock, call
from pydantic.networks import IPv4Address
from docker.errors import APIError

import tests.mocks as mock
from openfactory.docker.docker_access_layer import dal
from openfactory.models.user_notifications import user_notify
from openfactory import OpenFactoryCluster


mock_node = Mock()
mock_node.attrs = {
    'Status': {'Addr': '192.168.1.1'},
    'Spec': {'Labels': {}}
}


@patch("docker.DockerClient", return_value=mock.docker_client)
class TestOpenFactoryCluster(TestCase):
    """
    Unit tests for OpenFactoryCluster class
    """

    @classmethod
    def setUpClass(cls):
        dal.docker_client = mock.docker_client
        dal.docker_client.info = Mock(return_value={})
        dal.docker_client.nodes.list = Mock(return_value=[])
        dal.docker_url = 'manager node url'
        dal.ip = 'manager node ip'
        dal.worker_token = 'worker token'
        dal.manager_token = 'manager token'

        user_notify.setup(success_msg=Mock(),
                          fail_msg=Mock(),
                          info_msg=Mock(),
                          warning_msg=Mock())

    def setUp(self):
        """ Reset mocks and initialize cluster """
        mock_node.update.reset_mock()

        # Save original info mock
        original_info = dal.docker_client.info

        # Patch it temporarily just for construction
        dal.docker_client.info = Mock(return_value={
            "Name": "mock-node",
            "Swarm": {
                "LocalNodeState": "active",
                "ControlAvailable": True,
                "NodeID": "mock-node-id"
            }
        })
        self.cluster = OpenFactoryCluster()

        # Restore it back before setUp finishes
        dal.docker_client.info = original_info

    def test_add_label_no_label(self, *args):
        """ Test add_label when no explicit label is added """
        dal.docker_client.nodes.list = Mock(return_value=[mock_node])
        self.cluster.add_label('some_node_name', {'ip': IPv4Address('192.168.1.1')})

        expected_spec = {'Labels': {'name': 'some_node_name'}}
        mock_node.update.assert_called_once_with(expected_spec)

    def test_add_label(self, *args):
        """ Test add_label for some label """
        dal.docker_client.nodes.list = Mock(return_value=[mock_node])
        self.cluster.add_label('some_node_name', {'ip': IPv4Address('192.168.1.1'), 'labels': {'type': 'ofa'}})

        expected_spec = {'Labels': {'name': 'some_node_name', 'type': 'ofa'}}
        mock_node.update.assert_called_once_with(expected_spec)

    def test_add_label_node_not_exist(self, *args):
        """ Test add_label when node does not exist """
        dal.docker_client.nodes.list = Mock(return_value=[mock_node])
        self.cluster.add_label('some_node_name', {'ip': IPv4Address('192.168.1.111')})

        for node in dal.docker_client.nodes.list.return_value:
            node.update.assert_not_called()

    @patch('openfactory.openfactory_cluster.config')
    def test_create_managers(self, mock_config, mock_dockerclient):
        """ Test setup of managers """
        managers = {
            "manager1": {"ip": IPv4Address("123.123.1.1")},
            "manager2": {"ip": IPv4Address("123.123.2.2")}
        }
        mock_config.OPENFACTORY_USER = 'mock_user'
        mock_dockerclient.info = Mock(return_value={})
        self.cluster.create_managers(managers)

        mock_dockerclient.assert_any_call(base_url='ssh://mock_user@123.123.1.1')
        mock_dockerclient.assert_any_call(base_url='ssh://mock_user@123.123.2.2')
        user_notify.success.assert_any_call('Node "manager1 (123.123.1.1)" setup')
        user_notify.success.assert_any_call('Node "manager2 (123.123.2.2)" setup')
        self.assertIn(call(['manager node ip'], join_token='manager token'), mock.docker_swarm.join.call_args_list)

    @patch.object(OpenFactoryCluster, 'add_label')
    def test_create_manager_label(self, mock_add_label, *args):
        """ Test if managers are labeled """
        managers = {
            "manager1": {"ip": IPv4Address("123.123.1.1"), "labels": {"type": "ofa"}}
        }
        self.cluster.create_managers(managers)

        mock_add_label.assert_called_with('manager1', managers["manager1"])

    @patch('openfactory.openfactory_cluster.config')
    def test_create_workers(self, mock_config, mock_dockerclient):
        """ Test setup of workers """
        workers = {
            "worker1": {"ip": IPv4Address("123.123.1.1")},
            "worker2": {"ip": IPv4Address("123.123.2.2")}
        }
        mock_config.OPENFACTORY_USER = 'mock_user'
        mock_dockerclient.info = Mock(return_value={})
        self.cluster.create_workers(workers)

        mock_dockerclient.assert_any_call(base_url='ssh://mock_user@123.123.1.1')
        mock_dockerclient.assert_any_call(base_url='ssh://mock_user@123.123.2.2')
        user_notify.success.assert_any_call('Node "worker1 (123.123.1.1)" setup')
        user_notify.success.assert_any_call('Node "worker2 (123.123.2.2)" setup')
        self.assertIn(call(['manager node ip'], join_token='worker token'), mock.docker_swarm.join.call_args_list)

    @patch.object(OpenFactoryCluster, 'add_label')
    def test_create_worker_label(self, mock_add_label, *args):
        """ Test if workers are labeled """
        workers = {
            "worker1": {"ip": IPv4Address("123.123.1.1"), "labels": {"type": "ofa"}}
        }
        self.cluster.create_workers(workers)

        mock_add_label.assert_called_with('worker1', workers["worker1"])

    @patch('openfactory.openfactory_cluster.get_infrastructure_from_config_file')
    @patch.object(OpenFactoryCluster, 'create_workers')
    @patch.object(OpenFactoryCluster, 'create_managers')
    def test_create_infrastack_from_config_file(self, mock_create_managers, mock_create_workers, mock_get_infra, *args):
        """ Test setup of a base infrastructure """
        mock_get_infra.return_value = {
            'nodes': {
                'managers': {
                    'manager1': {'ip': IPv4Address('192.168.123.100'), 'labels': None},
                    'manager2': {'ip': IPv4Address('192.168.123.101'), 'labels': None}
                },
                'workers': {
                    'node1': {'ip': IPv4Address('192.168.123.111'), 'labels': None},
                    'node2': {'ip': IPv4Address('192.168.123.112'), 'labels': None}
                }
            }
        }

        self.cluster.create_infrastack_from_config_file('some_file.yml')

        mock_create_managers.assert_called_once_with(mock_get_infra.return_value['nodes']['managers'])
        mock_create_workers.assert_called_once_with(mock_get_infra.return_value['nodes']['workers'])

    @patch('openfactory.openfactory_cluster.dal')
    @patch('openfactory.openfactory_cluster.config')
    @patch('openfactory.openfactory_cluster.user_notify')
    def test_remove_workers_success(self, mock_user_notify, mock_config, mock_dal, mock_docker_client):
        """ Test successful removal of a worker node """
        mock_config.OPENFACTORY_USER = 'testuser'

        workers = {
            'worker1': {'ip': '192.168.1.10'}
        }
        node_ip_map = {
            '192.168.1.10': 'node_id_1'
        }

        # Setup mock node
        mock_node.attrs = {
            'Spec': {'Availability': 'active'},
            'Status': {'Addr': '192.168.1.10'}
        }
        mock_node.id = 'node_id_1'
        mock_dal.docker_client.nodes.get = Mock(return_value=mock_node)

        # Setup mock SSH Docker client
        mock_ssh_client = Mock()
        mock_docker_client.return_value = mock_ssh_client

        self.cluster.remove_workers(workers, node_ip_map)

        # Assert node was drained
        mock_user_notify.info.assert_any_call('Draining node worker1 ...')
        mock_node.update.assert_called_once()
        args, _ = mock_node.update.call_args
        assert args[0]['Availability'] == 'drain'

        # Assert SSH leave
        mock_docker_client.assert_called_once_with(base_url='ssh://testuser@192.168.1.10')
        mock_ssh_client.swarm.leave.assert_called_once()

        # Assert manager removal
        mock_dal.docker_client.api.remove_node.assert_called_once_with('node_id_1', force=True)
        mock_user_notify.success.assert_called_once_with('Removed node worker1')

    @patch('openfactory.openfactory_cluster.config')
    @patch('openfactory.openfactory_cluster.user_notify')
    @patch('openfactory.openfactory_cluster.docker.DockerClient')
    def test_remove_workers_missing_ip(self, mock_docker_client, mock_user_notify, mock_config, *args):
        """ Test worker removal is skipped if IP not in node_ip_map """
        workers = {
            'worker1': {'ip': '192.168.1.10'}
        }
        node_ip_map = {
            '192.168.1.99': 'node_id_1'
        }

        self.cluster.remove_workers(workers, node_ip_map)

        mock_user_notify.info.assert_not_called()
        mock_user_notify.success.assert_not_called()
        mock_docker_client.assert_not_called()

    @patch('openfactory.openfactory_cluster.config')
    @patch('openfactory.openfactory_cluster.user_notify')
    def test_remove_workers_api_error(self, mock_user_notify, mock_config, mock_docker_client):
        """ Test APIError during node removal is handled gracefully """
        mock_config.OPENFACTORY_USER = 'testuser'

        workers = {
            'worker1': {'ip': '192.168.1.10'}
        }
        node_ip_map = {
            '192.168.1.10': 'node_id_1'
        }

        # Simulate failure
        dal.docker_client.nodes.get = Mock(side_effect=APIError("API failed"))

        self.cluster.remove_workers(workers, node_ip_map)

        mock_user_notify.fail.assert_called()
        msg = mock_user_notify.fail.call_args[0][0]
        assert 'Node "worker1" could not be removed' in msg

    @patch('openfactory.openfactory_cluster.get_infrastructure_from_config_file')
    @patch("openfactory.openfactory_cluster.config")
    def test_remove_infrastack_from_config_file(self, mock_config, mock_get_config, mock_docker_client, *args):
        """ Test teardown of infrastack using a mocked config structure """
        mock_config.OPENFACTORY_USER = 'mock_user'

        mock_get_config.return_value = {
            'nodes': {
                'workers': {
                    'worker1': {
                        'ip': IPv4Address('192.168.123.111')
                    }
                }
            }
        }

        # Mock node
        mock_node.attrs['Status']['Addr'] = '192.168.123.111'
        mock_node.id = 'mock_id'
        dal.docker_client.nodes.list = Mock(return_value=[mock_node])
        dal.docker_client.nodes.get = Mock(return_value=mock_node)

        self.cluster.remove_infrastack_from_config_file('fake/path/to/config.yml')

        # Assert node was drained
        mock_node.update.assert_called_once()
        update_args, _ = mock_node.update.call_args
        self.assertEqual(update_args[0]['Availability'], 'drain')

        # Assert node was removed via manager
        dal.docker_client.api.remove_node.assert_called_once_with('mock_id', force=True)

        # Assert DockerClient used SSH to access the node
        mock_docker_client.assert_called_once_with(base_url='ssh://mock_user@192.168.123.111')
        mock.docker_client.swarm.leave.assert_called_once_with()
