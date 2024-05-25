import tempfile
import os
import tarfile
import docker
from requests.exceptions import ConnectionError
from paramiko.ssh_exception import SSHException
from unittest import TestCase
from unittest.mock import patch, Mock
import docker.errors
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from openfactory.models.base import Base
from openfactory.models.containers import DockerContainer, _docker_clients
from openfactory.models.nodes import Node
from openfactory.exceptions import OFAException
import tests.mocks as mock


# Mock infrastructure
def create_node():
    node = Node(
        node_name='manager',
        node_ip='123.456.7.891',
        network='test-net'
    )
    return node


@patch("docker.DockerClient", return_value=mock.docker_client)
class TestDockerContainer(TestCase):
    """
    Unit tests for DockerContainer model
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

        """ reset mocks """
        mock.docker_client.reset_mock()
        mock.docker_container.reset_mock()
        mock.docker_images.reset_mock()

    def cleanup(self, *args):
        """
        Clean up all containers and nodes
        """
        self.session.rollback()
        # remove containers
        for cont in self.session.scalars(select(DockerContainer)):
            self.session.delete(cont)
            self.session.commit()
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

        # clear docker clients
        _docker_clients.clear()

    def test_class_parent(self, *args):
        """
        Test parent of class is Base
        """
        self.assertEqual(DockerContainer.__bases__[0], Base)

    def test_table_name(self, *args):
        """
        Test table name
        """
        self.assertEqual(DockerContainer.__tablename__, 'docker_container')

    def test_container_setup(self, mock_DockerClient):
        """
        Test setup and tear down of a DockerContainer
        """
        node = create_node()
        self.session.add_all([node])
        self.session.commit()

        mock_DockerClient.reset_mock()
        container = DockerContainer(
            image='tester/test',
            name='test_cont',
            command='run some cmd',
            cpus=1,
            node=node)
        self.session.add_all([container])
        self.session.commit()

        # use correct docker client
        mock_DockerClient.assert_called_once_with(base_url=node.docker_url)

        # pull Docker image
        mock.docker_images.get.assert_called_once_with('tester/test')
        mock.docker_images.pull.assert_called_once_with('tester/test')

        # create correctly container
        args, kwargs = mock.docker_containers.create.call_args
        self.assertEqual(args[0], 'tester/test')
        self.assertEqual(kwargs['name'], 'test_cont')
        self.assertEqual(kwargs['detach'], True)
        self.assertEqual(kwargs['environment'], [])
        self.assertEqual(kwargs['ports'], {})
        self.assertEqual(kwargs['command'], 'run some cmd')
        self.assertEqual(kwargs['network'], node.network)
        self.assertEqual(kwargs['nano_cpus'], container.cpus*1E9)

        # entry in database is correct
        query = select(DockerContainer).where(DockerContainer.name == "test_cont")
        cont = self.session.execute(query).first()
        self.assertEqual(cont[0].image, 'tester/test')
        self.assertEqual(cont[0].command, 'run some cmd')
        self.assertEqual(cont[0].cpus, 1)
        self.assertEqual(cont[0].node, node)

        # tear down container
        mock_DockerClient.reset_mock()
        del _docker_clients[node.docker_url]  # force to reconnect
        self.session.delete(cont[0])
        self.session.commit()

        # use correct docker client
        mock_DockerClient.assert_called_once_with(base_url=node.docker_url)

        # fetch correct container
        mock.docker_containers.get.assert_called_once_with(container.name)

        # stops and removes container
        mock.docker_container.stop.assert_called_once()
        mock.docker_container.remove.assert_called_once()

        # clean up
        self.cleanup()

    def test_setup_container_host_down(self, mock_DockerClient):
        """
        Test insert of a DockerContainer when host is down
        """
        node = create_node()
        self.session.add_all([node])
        self.session.commit()

        container = DockerContainer(
            image='tester/test',
            name='test_cont',
            command='run some cmd',
            node=node)

        # Mock SSHException
        _docker_clients.clear()
        mock_DockerClient.side_effect = SSHException
        self.session.add_all([container])
        self.assertRaises(OFAException, self.session.commit)
        self.session.rollback()

        # Mock ConnectionError
        _docker_clients.clear()
        mock_DockerClient.side_effect = ConnectionError
        self.session.add_all([container])
        self.assertRaises(OFAException, self.session.commit)
        self.session.rollback()

        # clean up
        mock_DockerClient.side_effect = None
        self.cleanup()

    def test_delete_container_host_down(self, mock_DockerClient):
        """
        Test delete of a DockerContainer when host is down
        """
        node = create_node()
        container = DockerContainer(
            image='tester/test',
            name='test_cont',
            command='run some cmd',
            node=node)
        self.session.add_all([node, container])
        self.session.commit()

        # mock node down
        _docker_clients[container.docker_url].ping.side_effect = ConnectionError('Mocking connection error')
        mock_DockerClient.side_effect = ConnectionError('Mocking connection error')

        # check OFAException exception raised
        self.session.delete(container)
        try:
            self.session.commit()
        except OFAException:
            self.session.rollback()

        # check container was not removed
        query = select(DockerContainer).where(DockerContainer.name == "test_cont")
        self.assertEqual(self.session.execute(query).one(), (container,))

        # clean up
        _docker_clients[container.docker_url].ping.side_effect = None
        mock_DockerClient.side_effect = None
        self.cleanup()

    def test_delete_db_entry_if_no_docker_container(self, *args):
        """
        Test databse entry is removed even if Docker container does not exist
        """
        node = create_node()
        self.session.add_all([node])
        self.session.commit()

        container = DockerContainer(
            image='tester/test',
            name='test_cont',
            command='run some cmd',
            cpus=1,
            node=node)
        self.session.add_all([container])
        self.session.commit()

        mock.docker_containers.get.side_effect = docker.errors.DockerException()
        self.session.delete(container)
        self.session.commit()

        # check databse entry was removed
        query = select(DockerContainer).where(DockerContainer.name == "test_cont")
        self.assertIsNone(self.session.execute(query).one_or_none())

        # clean up
        mock.docker_containers.get.side_effect = None
        self.cleanup()

    def test_cpus(self, *args):
        """
        Test DockerContainer.cpu is handled as expected
        """
        node = create_node()
        self.session.add_all([node])
        self.session.commit()

        cont1 = DockerContainer(
            image='tester/test1',
            name='test_cont1',
            command='run some cmd 1',
            node=node)
        cont2 = DockerContainer(
            image='tester/test2',
            name='test_cont2',
            command='run some cmd 2',
            cpus=16,
            node=node)
        self.session.add_all([cont1, cont2])
        self.session.commit()

        # if no cpu provided, use maximal number from node
        query = select(DockerContainer).where(DockerContainer.name == "test_cont1")
        cont_1 = self.session.execute(query).one()
        self.assertEqual(cont_1[0].cpus, 5)

        # if too many cpus provided, use maximal number from node
        query = select(DockerContainer).where(DockerContainer.name == "test_cont2")
        cont_2 = self.session.execute(query).one()
        self.assertEqual(cont_2[0].cpus, 5)

        # clean up
        self.cleanup()

    def test_name_unique(self, *args):
        """
        Test DockerContainer.name is required to be unique
        """
        node = create_node()
        self.session.add_all([node])
        self.session.commit()
        cont1 = DockerContainer(
            image='tester/test1',
            name='test_cont1',
            command='run some cmd 1',
            cpus=1,
            node=node)
        cont2 = DockerContainer(
            image='tester/test2',
            name='test_cont1',
            command='run some cmd 2',
            cpus=2,
            node=node)
        self.session.add_all([cont1, cont2])
        self.assertRaises(IntegrityError, self.session.commit)

        # clean up
        self.cleanup()

    def test_docker_client_connect(self, mock_DockerClient, *args):
        """
        Test Docker client connection established when using first time
        """
        node = create_node()
        container = DockerContainer(
            image='tester/test',
            name='test_cont',
            command='run some cmd',
            cpus=1,
            node=node)

        container.docker_client
        mock_DockerClient.assert_called_once_with(base_url=node.docker_url)

        # clean up
        self.cleanup()

    def test_docker_client(self, mock_DockerClient, *args):
        """
        Test hybride property 'docker_client' of a DockerContainer
        """
        node = create_node()
        container = DockerContainer(
            image='tester/test',
            name='test_cont',
            command='run some cmd',
            cpus=1,
            node=node)
        self.assertEqual(container.docker_client, _docker_clients[node.docker_url])

        # clean up
        self.cleanup()

    def test_docker_url(self, *args):
        """
        Test hybride property 'docker_url' of a DockerContainer
        """
        node = create_node()
        container = DockerContainer(
            image='tester/test',
            name='test_cont',
            command='run some cmd',
            cpus=1,
            node=node)
        self.session.add_all([node, container])
        self.session.commit()

        self.assertEqual(container.docker_url, node.docker_url)

        # clean up
        self.cleanup()

    def test_network(self, *args):
        """
        Test hybride property 'network' of a DockerContainer
        """
        node = create_node()
        container = DockerContainer(
            image='tester/test',
            name='test_cont',
            command='run some cmd',
            cpus=1,
            node=node)
        self.session.add_all([node, container])
        self.session.commit()

        self.assertEqual(container.network, 'test-net')

        # clean up
        self.cleanup()

    def test_container(self, mock_DockerClient):
        """
        Test hybride property 'container' of a DockerContainer
        """
        node = create_node()
        container = DockerContainer(
            image='tester/test',
            name='test_cont',
            command='run some cmd',
            cpus=1,
            node=node)
        self.session.add_all([node, container])
        self.session.commit()

        mock_DockerClient.reset_mock()
        del _docker_clients[node.docker_url]  # force to reconnect
        docker_cont = container.container

        # use correct docker client
        mock_DockerClient.assert_called_once_with(base_url=node.docker_url)

        # fetch correct container
        mock.docker_containers.get.assert_called_once_with(container.name)
        self.assertEqual(docker_cont, mock.docker_container)

        # clean up
        self.cleanup()

    def test_container_none_existent(self, mock_DockerClient):
        """
        Test hybride property 'container' of a DockerContainer in case container does not exist
        """
        node = create_node()
        container = DockerContainer(
            image='tester/test',
            name='test_cont',
            command='run some cmd',
            node=node)
        self.session.add_all([node, container])
        self.session.commit()

        del _docker_clients[container.docker_url]
        mock_DockerClient.side_effect = docker.errors.NotFound('Mocking none existing container')
        self.assertIsNone(container.container)
        self.assertEqual(container._status_error, 'no container')

        # clean up
        mock_DockerClient.side_effect = None
        self.cleanup()

    def test_container_no_connection_to_node(self, mock_DockerClient):
        """
        Test hybride property 'container' of a DockerContainer in case connection to node lost
        """
        node = create_node()
        container = DockerContainer(
            image='tester/test',
            name='test_cont',
            command='run some cmd',
            node=node)
        self.session.add_all([node, container])
        self.session.commit()

        del _docker_clients[container.docker_url]
        mock_DockerClient.side_effect = SSHException('Mocking SSH connection error')
        self.assertIsNone(container.container)
        self.assertEqual(container._status_error, 'node down')

        # clean up
        mock_DockerClient.side_effect = None
        self.cleanup()

    def test_status(self, *args):
        """
        Test hybride property 'status' of a DockerContainer
        """
        node = create_node()
        container = DockerContainer(
            image='tester/test',
            name='test_cont',
            command='run some cmd',
            cpus=1,
            node=node)
        self.session.add_all([node, container])
        self.session.commit()

        self.assertEqual(container.status, 'running')

        # clean up
        self.cleanup()

    def test_status_no_docker_container(self, *args):
        """
        Test hybride property 'status' of a DockerContainer in case no actual Docker container exists
        """
        container = DockerContainer()
        with patch('openfactory.models.containers.DockerContainer.container'):
            container.container = None
            container._status_error = 'This should be returned'
            self.assertEqual(container.status, 'This should be returned')

    def test_add_file(self, mock_DockerClient):
        """
        Test DockerContainer.add_file
        """
        node = create_node()
        container = DockerContainer(
            image='tester/test',
            name='test_cont',
            command='run some cmd',
            cpus=1,
            node=node)
        self.session.add_all([node, container])
        self.session.commit()

        # mock some file
        tmp_dir = tempfile.TemporaryDirectory()
        src = os.path.join(tmp_dir.name, 'file_to_upload.txt')
        with open(src, 'w') as f:
            f.write('Some important text')

        # compute content of tar archive
        tar_file = os.path.join(tmp_dir.name, 'files.tar')
        with tarfile.open(tar_file, mode='w') as tar:
            tar.add(src, arcname=os.path.basename('/some/destination/folder/data.txt'))
        with open(tar_file, 'rb') as f:
            data = f.read()

        container.add_file(src, '/some/destination/folder/data.txt')
        mock.docker_container.put_archive.assert_called_once_with('/some/destination/folder', data)

        # clean up
        tmp_dir.cleanup()
        self.cleanup()

    def test_add_file_no_container(self, *args):
        """
        Test DockerContainer.add_file raises OFAException when no container
        """
        # mock some file
        tmp_dir = tempfile.TemporaryDirectory()
        src = os.path.join(tmp_dir.name, 'file_to_upload.txt')
        with open(src, 'w') as f:
            f.write('Some important text')

        cont = DockerContainer()

        with patch('openfactory.models.containers.DockerContainer.container'):
            cont.container = None
            self.assertRaises(OFAException, cont.add_file, src, '/some/destination/folder/data.txt')

        # clean up
        tmp_dir.cleanup()

    def test_start(self, *args):
        """
        Test DockerContainer.start
        """
        cont = DockerContainer()
        with patch('openfactory.models.containers.DockerContainer.container'):
            cont.container = Mock()
            cont.container.start = Mock()
            cont.start()
            cont.container.start.assert_called()

    def test_start_no_container(self, *args):
        """
        Test DockerContainer.start raises OFAException when no container
        """
        cont = DockerContainer()
        with patch('openfactory.models.containers.DockerContainer.container'):
            cont.container = None
            self.assertRaises(OFAException, cont.start)

    def test_stop(self, mock_DockerClient):
        """
        Test DockerContainer.start
        """
        cont = DockerContainer()
        with patch('openfactory.models.containers.DockerContainer.container'):
            cont.container = Mock()
            cont.container.stop = Mock()
            cont.stop()
            cont.container.stop.assert_called()

    def test_stop_no_container(self, *args):
        """
        Test DockerContainer.stop raises OFAException when no container
        """
        cont = DockerContainer()
        with patch('openfactory.models.containers.DockerContainer.container'):
            cont.container = None
            self.assertRaises(OFAException, cont.stop)
