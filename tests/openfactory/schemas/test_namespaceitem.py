import unittest
from pydantic import ValidationError
from openfactory.schemas.uns import NamespaceItem


class TestNamespaceItem(unittest.TestCase):
    """
    Test class NamespaceItem
    """

    def test_valid_single_key(self):
        """ Test single key """
        item = NamespaceItem({'area': 'A1'})
        self.assertEqual(item.key(), 'area')
        self.assertEqual(item.value(), 'A1')

    def test_valid_single_key_list_value(self):
        """ Test key with list """
        item = NamespaceItem({'station': ['S1', 'S2']})
        self.assertEqual(item.key(), 'station')
        self.assertEqual(item.value(), ['S1', 'S2'])

    def test_invalid_zero_keys(self):
        """ Test case when no keys """
        with self.assertRaises(ValidationError):
            NamespaceItem({})

    def test_invalid_multiple_keys(self):
        """ Test when multiple keys """
        with self.assertRaises(ValidationError):
            NamespaceItem({'inc': 'I1', 'area': 'A1'})
