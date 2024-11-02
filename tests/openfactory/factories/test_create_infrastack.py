import os
from unittest import TestCase
from unittest.mock import patch, Mock, call
import tests.mocks as mock

from openfactory.docker.docker_access_layer import dal
from openfactory.factories import create_infrastack
from openfactory.factories.create_infra import add_label, create_managers, create_workers
from openfactory.models.user_notifications import user_notify


# Mock a node
mock_node = Mock()
mock_node.attrs = {
    'Status': {'Addr': '192.168.1.1'},
    'Spec': {'Labels': {}}
}


@patch("docker.DockerClient", return_value=mock.docker_client)
class Test_create_infrastack(TestCase):
    """
    Unit tests for create_infrastack factory
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
                          info_msg=Mock())

    @classmethod
    def setUp(self):
        """ Reset mocks """
        mock_node.update.reset_mock()

    def test_add_label_no_label(self, *args):
        """ Test add_label when no explicit label is added """
        dal.docker_client.nodes.list = Mock(return_value=[mock_node])
        add_label('some_node_name', {'ip': '192.168.1.1'})

        expected_spec = {'Labels': {'name': 'some_node_name'}}
        mock_node.update.assert_called_once_with(expected_spec)

    def test_add_label(self, *args):
        """ Test add_label for some label """
        dal.docker_client.nodes.list = Mock(return_value=[mock_node])
        add_label('some_node_name', {'ip': '192.168.1.1', 'labels': {'type': 'ofa'}})

        expected_spec = {'Labels': {'name': 'some_node_name', 'type': 'ofa'}}
        mock_node.update.assert_called_once_with(expected_spec)

    def test_add_label_node_not_exist(self, *args):
        """ Test add_label when node does not exist """
        dal.docker_client.nodes.list = Mock(return_value=[mock_node])
        add_label('some_node_name', {'ip': '192.168.1.111'})

        for node in dal.docker_client.nodes.list.return_value:
            node.update.assert_not_called()

    @patch('openfactory.factories.create_infra.config')
    def test_create_managers(self, mock_config, mock_dockerclient):
        """
        Test setup of managers
        """
        managers = {
            "manager1": {"ip": "123.123.1.1"},
            "manager2": {"ip": "123.123.2.2"}
            }
        mock_config.OPENFACTORY_USER = 'mock_user'
        mock_dockerclient.info = Mock(return_value={})
        create_managers(managers)

        mock_dockerclient.assert_any_call(base_url='ssh://mock_user@123.123.1.1')
        mock_dockerclient.assert_any_call(base_url='ssh://mock_user@123.123.2.2')
        user_notify.success.assert_any_call('Node "manager1 (123.123.1.1)" setup')
        user_notify.success.assert_any_call('Node "manager2 (123.123.2.2)" setup')
        self.assertIn(call(['manager node ip'], join_token='manager token'), mock.docker_swarm.join.call_args_list)

    @patch('openfactory.factories.create_infra.add_label')
    def test_create_manager_label(self, mock_add_label, *args):
        """
        Test if managers are labeled
        """
        managers = {
            "manager1": {"ip": "123.123.1.1", "labels": {"type": "ofa"}}
            }
        create_managers(managers)

        mock_add_label.assert_called_with('manager1', {"ip": "123.123.1.1", "labels": {"type": "ofa"}})

    @patch('openfactory.factories.create_infra.config')
    def test_create_workers(self, mock_config, mock_dockerclient):
        """
        Test setup of workers
        """
        workers = {
            "worker1": {"ip": "123.123.1.1"},
            "worker2": {"ip": "123.123.2.2"}
            }
        mock_config.OPENFACTORY_USER = 'mock_user'
        mock_dockerclient.info = Mock(return_value={})
        create_workers(workers)

        mock_dockerclient.assert_any_call(base_url='ssh://mock_user@123.123.1.1')
        mock_dockerclient.assert_any_call(base_url='ssh://mock_user@123.123.2.2')
        user_notify.success.assert_any_call('Node "worker1 (123.123.1.1)" setup')
        user_notify.success.assert_any_call('Node "worker2 (123.123.2.2)" setup')
        self.assertIn(call(['manager node ip'], join_token='worker token'), mock.docker_swarm.join.call_args_list)

    @patch('openfactory.factories.create_infra.add_label')
    def test_create_worker_label(self, mock_add_label, *args):
        """
        Test if workers are labeled
        """
        workers = {
            "worker1": {"ip": "123.123.1.1", "labels": {"type": "ofa"}}
            }
        create_managers(workers)

        mock_add_label.assert_called_with('worker1', {"ip": "123.123.1.1", "labels": {"type": "ofa"}})

    @patch('openfactory.factories.create_infra.create_workers')
    @patch('openfactory.factories.create_infra.create_managers')
    def test_create_infrastack(self, mock_create_managers, mock_create_workers, *args):
        """
        Test setup of a base infrastructure
        """
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'mocks/infra/base_infra_mock.yml')
        create_infrastack(config_file)

        # check if manager is setup correctly
        mock_create_managers.assert_called_once_with({'manager1': {'ip': '192.168.123.100', 'labels': None},
                                                      'manager2': {'ip': '192.168.123.101', 'labels': None}})

        # check if workers are setup correctly
        mock_create_workers.assert_called_once_with({'node1': {'ip': '192.168.123.111', 'labels': None},
                                                     'node2': {'ip': '192.168.123.112', 'labels': None}})
