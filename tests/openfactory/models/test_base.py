from unittest import TestCase
from sqlalchemy.orm import DeclarativeBase
from openfactory.models.base import Base


class TestNodes(TestCase):
    """
    Unit tests for Base model
    """

    def test_class_parent(self, *args):
        """
        Test parent of class is DeclarativeBase
        """
        self.assertEqual(Base.__bases__[0], DeclarativeBase)
