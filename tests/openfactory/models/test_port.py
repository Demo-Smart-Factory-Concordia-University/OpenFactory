from unittest import TestCase
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from openfactory.models.base import Base
from openfactory.models.containers import Port
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
class TestPort(TestCase):
    """
    Unit tests for Port model
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
        """ rollback all transactions """
        self.session.rollback()
        self.session.close()

    def test_class_parent(self, *args):
        """
        Test parent of class is Base
        """
        self.assertEqual(Port.__bases__[0], Base)

    def test_table_name(self, *args):
        """
        Test table name
        """
        self.assertEqual(Port.__tablename__, 'container_ports')

    def test_setup_port(self, *args):
        """
        Test setup and tear down of a EnvVar
        """
        port = Port(
            container_port='test:5000',
            host_port=6000)
        self.session.add_all([port])
        self.session.commit()

        # entry in database is correct
        query = select(Port).where(Port.id == port.id)
        var = self.session.execute(query).first()
        self.assertEqual(var[0].container_port, 'test:5000')
        self.assertEqual(var[0].host_port, 6000)

        # clean up
        self.session.delete(var[0])
        self.session.commit()

    def test_attach_port_to_container(self, *args):
        """
        Test attaching Port to a DockerContainer
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

        port1 = Port(
            container_port='test1:5000',
            host_port=6001)
        port2 = Port(
            container_port='test2:5000',
            host_port=6002)
        container.ports = [port1, port2]
        self.session.commit()

        # entry in database is correct
        query = select(DockerContainer).where(container.id == container.id)
        cont = self.session.execute(query).first()
        self.assertEqual(cont[0].ports[0].container_port, 'test1:5000')
        self.assertEqual(cont[0].ports[0].host_port, 6001)
        self.assertEqual(cont[0].ports[1].container_port, 'test2:5000')
        self.assertEqual(cont[0].ports[1].host_port, 6002)

        # Port are removed from database after removing the DockerContainer
        self.session.delete(container)
        self.session.commit()
        query = select(Port).where(Port.id == port1.id)
        p = self.session.execute(query).first()
        self.assertEqual(p, None)
        query = select(Port).where(Port.id == port2.id)
        p = self.session.execute(query).first()
        self.assertEqual(p, None)

        # clean up
        self.session.delete(node)
        self.session.commit()
