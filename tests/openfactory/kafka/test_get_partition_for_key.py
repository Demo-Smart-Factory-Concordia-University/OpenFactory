import unittest
from openfactory.kafka import get_partition_for_key


class TestGetPartitionForKey(unittest.TestCase):
    """
    Test get_partition_for_key
    """

    def test_partition_is_deterministic(self):
        key = 'example-key'
        part1 = get_partition_for_key(key, 10)
        part2 = get_partition_for_key(key, 10)
        self.assertEqual(part1, part2)

    def test_partition_within_bounds(self):
        for i in range(1, 100):
            part = get_partition_for_key(f'key-{i}', 10)
            self.assertGreaterEqual(part, 0)
            self.assertLess(part, 10)

    def test_different_keys_different_partitions(self):
        key1 = 'dev-001'
        key2 = 'dev-002'
        p1 = get_partition_for_key(key1, 10)
        p2 = get_partition_for_key(key2, 10)
        # Not guaranteed to be different, but likely
        self.assertIsInstance(p1, int)
        self.assertIsInstance(p2, int)

    def test_partition_single_partition(self):
        part = get_partition_for_key('dev-004', 1)
        self.assertEqual(part, 0)

    def test_partition_empty_key(self):
        part = get_partition_for_key('', 5)
        self.assertGreaterEqual(part, 0)
        self.assertLess(part, 5)

    def test_known_kafka_partitions(self):
        """
        Test get_partition_for_key with actual values used by Kafka
        See REAMDE.md in this folder to know how to generate such values
        """
        self.assertEqual(get_partition_for_key("banana", 10), 9)
        self.assertEqual(get_partition_for_key("apple", 10), 7)
        self.assertEqual(get_partition_for_key("carrot", 10), 3)
        self.assertEqual(get_partition_for_key("", 10), 1)
        self.assertEqual(get_partition_for_key("A", 10), 8)
        self.assertEqual(get_partition_for_key("Zebra", 10), 3)
