from unittest import TestCase
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from openfactory.models.base import Base
from openfactory.models.containers import EnvVar
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
class TestEnvVar(TestCase):
    """
    Unit tests for EnvVar model
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
        self.assertEqual(EnvVar.__bases__[0], Base)

    def test_table_name(self, *args):
        """
        Test table name
        """
        self.assertEqual(EnvVar.__tablename__, 'container_envVars')

    def test_setup_envvar(self, *args):
        """
        Test setup and tear down of a EnvVar
        """
        envvar = EnvVar(
            variable='test_var',
            value='test_value')
        self.session.add_all([envvar])
        self.session.commit()

        # entry in database is correct
        query = select(EnvVar).where(EnvVar.id == envvar.id)
        var = self.session.execute(query).first()
        self.assertEqual(var[0].variable, 'test_var')
        self.assertEqual(var[0].value, 'test_value')

        # clean up
        self.session.delete(var[0])
        self.session.commit()

    def test_attach_envvar_to_container(self, *args):
        """
        Test attaching EnvVar to a DockerContainer
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

        envvar1 = EnvVar(
            variable='test_var1',
            value='test_value1')
        envvar2 = EnvVar(
            variable='test_var2',
            value='test_value2')
        container.environment = [envvar1, envvar2]
        self.session.commit()

        # entry in database is correct
        query = select(DockerContainer).where(container.id == container.id)
        cont = self.session.execute(query).first()
        self.assertEqual(cont[0].environment[0].variable, 'test_var1')
        self.assertEqual(cont[0].environment[0].value, 'test_value1')
        self.assertEqual(cont[0].environment[1].variable, 'test_var2')
        self.assertEqual(cont[0].environment[1].value, 'test_value2')

        # EnvVar are removed from database after removing the DockerContainer
        self.session.delete(container)
        self.session.commit()
        query = select(EnvVar).where(EnvVar.id == envvar1.id)
        var = self.session.execute(query).first()
        self.assertEqual(var, None)
        query = select(EnvVar).where(EnvVar.id == envvar2.id)
        var = self.session.execute(query).first()
        self.assertEqual(var, None)

        # clean up
        self.session.delete(node)
        self.session.commit()
