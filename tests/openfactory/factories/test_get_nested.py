from unittest import TestCase
from openfactory.factories.agents import get_nested


class Test_get_nested(TestCase):
    """
    Test get_nested
    """

    def test_valid_nested_keys(self):
        data = {'a': {'b': {'c': 'value'}}}
        keys = ['a', 'b', 'c']
        self.assertEqual(get_nested(data, keys), 'value')

    def test_missing_keys(self):
        data = {'a': {'b': {}}}
        keys = ['a', 'b', 'c']
        self.assertIsNone(get_nested(data, keys))

    def test_default_value_for_missing_keys(self):
        data = {'a': {'b': {}}}
        keys = ['a', 'b', 'c']
        self.assertEqual(get_nested(data, keys, default='default'), 'default')
