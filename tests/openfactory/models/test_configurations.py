from unittest import TestCase
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from openfactory.models.base import Base
from openfactory.models.configurations import Configuration


class TestInfraConfiguration(TestCase):
    """
    Unit tests for InfraStack model
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

    def test_class_parent(self, *args):
        """
        Test parent of class is Base
        """
        self.assertEqual(Configuration.__bases__[0], Base)

    def test_table_name(self, *args):
        """
        Test table name
        """
        self.assertEqual(Configuration.__tablename__, 'configurations')

    def test_configuration_setup(self, *args):
        """
        Test setup and tear down of a Configuration
        """
        configuration = Configuration(
            key='test_key',
            value='test_value',
            description='this is a test')
        self.session.add_all([configuration])
        self.session.commit()

        query = select(Configuration).where(Configuration.key == "test_key")
        config = self.session.execute(query).first()
        self.assertEqual(config[0].key, 'test_key')
        self.assertEqual(config[0].value, 'test_value')
        self.assertEqual(config[0].description, 'this is a test')

        self.session.delete(config[0])
        self.session.commit()

    def test_key_unique(self, *args):
        """
        Test Configuration.key is required to be unique
        """
        config1 = Configuration(
            key='test_key',
            value='test_value1',
            description='this is a test 1')
        config2 = Configuration(
            key='test_key',
            value='test_value2',
            description='this is a test 2')
        self.session.add_all([config1, config2])
        self.assertRaises(IntegrityError, self.session.commit)
        self.session.rollback()
