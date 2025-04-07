import unittest
from openfactory.kafka import CaseInsensitiveDict


class TestCaseInsensitiveDict(unittest.TestCase):
    """
    Test class CaseInsensitiveDict
    """

    def setUp(self):
        self.cid = CaseInsensitiveDict({
            'Foo': 1,
            'bAr': 2,
            'BAZ': 3
        })

    def test_getitem_case_insensitive(self):
        self.assertEqual(self.cid['foo'], 1)
        self.assertEqual(self.cid['FOO'], 1)
        self.assertEqual(self.cid['Bar'], 2)
        self.assertEqual(self.cid['baz'], 3)

    def test_getitem_case_preserved_in_storage(self):
        # Internally keys stay in original form
        self.assertIn('Foo', self.cid)
        self.assertNotIn('foo', self.cid)  # because __contains__ not overridden

    def test_getitem_keyerror(self):
        with self.assertRaises(KeyError):
            _ = self.cid['nope']
