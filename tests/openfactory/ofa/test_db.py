from unittest import TestCase
from unittest.mock import patch
from openfactory.ofa.db import DataAccessLayer
from openfactory.ofa.db import db
from openfactory.exceptions import OFAConfigurationException


class TestDataAccessLayer(TestCase):
    """
    Unit tests for DataAccessLayer
    """

    @patch("openfactory.ofa.db.create_engine", return_value='test engine')
    @patch("openfactory.ofa.db.Session")
    def test_connect(self, mock_Session, mock_create_engine):
        """
        Test connect method
        """
        d = DataAccessLayer()
        d.conn_uri = 'test uri'
        d.connect()
        mock_create_engine.called_once_with('test uri')
        mock_Session.called_once_with('test engine')

    def test_connect_no_uri(self):
        """
        Test if error raised when connect called without conn_uri defined
        """
        d = DataAccessLayer()
        self.assertRaises(OFAConfigurationException, d.connect)

    def test_dby(self):
        """
        Test if db type is DataAccessLayer
        """
        self.assertIsInstance(db, DataAccessLayer)
