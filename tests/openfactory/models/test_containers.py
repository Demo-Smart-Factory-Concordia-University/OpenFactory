import tempfile
import os
import tarfile
from unittest import TestCase
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from openfactory.models.base import Base
from openfactory.models.containers import DockerContainer
from openfactory.models.nodes import Node
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

    @classmethod
    def tearDown(self, *args):
        """ rollback all transactions """
        self.session.rollback()

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
        mock.docker_client.close.assert_called_once()

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
        self.session.delete(cont[0])
        self.session.commit()

        # use correct docker client
        mock_DockerClient.assert_called_once_with(base_url=node.docker_url)
        mock.docker_client.close.assert_called_once()

        # fetch correct container
        mock.docker_containers.get.assert_called_once_with(container.name)

        # stops and removes container
        mock.docker_container.stop.assert_called_once()
        mock.docker_container.remove.assert_called_once()

        # clean up
        self.session.delete(node)
        self.session.commit()

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
        cont_1 = self.session.execute(query).first()
        self.assertEqual(cont_1[0].cpus, 5)

        # if too many cpus provided, use maximal number from node
        query = select(DockerContainer).where(DockerContainer.name == "test_cont2")
        cont_2 = self.session.execute(query).first()
        self.assertEqual(cont_2[0].cpus, 5)

        # clean up
        self.session.delete(cont1)
        self.session.delete(cont2)
        self.session.delete(node)
        self.session.commit()

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
        self.session.rollback()
        self.session.delete(node)
        self.session.commit()

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
        self.session.delete(container)
        self.session.delete(node)
        self.session.commit()

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
        self.session.delete(container)
        self.session.delete(node)
        self.session.commit()

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
        docker_cont = container.container

        # use correct docker client
        mock_DockerClient.assert_called_once_with(base_url=node.docker_url)
        mock.docker_client.close.assert_called_once()

        # fetch correct container
        mock.docker_containers.get.assert_called_once_with(container.name)
        self.assertEqual(docker_cont, mock.docker_container)

        # clean up
        self.session.delete(container)
        self.session.delete(node)
        self.session.commit()

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
        self.session.delete(container)
        self.session.delete(node)
        self.session.commit()

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
        self.session.delete(container)
        self.session.delete(node)
        self.session.commit()

    def test_start(self, mock_DockerClient):
        """
        Test DockerContainer.start
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
        container.start()

        # use correct docker client
        mock_DockerClient.assert_called_once_with(base_url=node.docker_url)
        mock.docker_client.close.assert_called_once()

        # fetch correct container and start it
        mock.docker_containers.get.assert_called_once_with(container.name)
        mock.docker_container.start.assert_called_once()

        # clean up
        self.session.delete(container)
        self.session.delete(node)
        self.session.commit()

    def test_stop(self, mock_DockerClient):
        """
        Test DockerContainer.start
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
        container.stop()

        # use correct docker client
        mock_DockerClient.assert_called_once_with(base_url=node.docker_url)
        mock.docker_client.close.assert_called_once()

        # fetch correct container and start it
        mock.docker_containers.get.assert_called_once_with(container.name)
        mock.docker_container.stop.assert_called_once()

        # clean up
        self.session.delete(container)
        self.session.delete(node)
        self.session.commit()
