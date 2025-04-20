import unittest
import time
import pandas as pd
from openfactory.kafka import KSQLDBClient
import openfactory.config as config


class TestKSQLDBStreamLifecycle(unittest.TestCase):
    """
    Integration tests for KSQLDBClient
    """

    @classmethod
    def setUpClass(cls):
        cls.ksql = KSQLDBClient(config.KSQLDB_URL)
        cls.stream_name = "test_stream"

    @classmethod
    def tearDownClass(cls):
        cls.ksql.statement_query(f"DROP STREAM IF EXISTS {cls.stream_name} DELETE TOPIC;")
        cls.ksql.close()

    def test_stream_lifecycle(self):
        # Clean up any existing stream and topic
        self.ksql.statement_query(f"DROP STREAM IF EXISTS {self.stream_name} DELETE TOPIC;")

        # 1. Create new stream
        self.ksql.statement_query(f"""
            CREATE STREAM {self.stream_name} (
                ASSET_UUID VARCHAR KEY,
                id VARCHAR,
                value VARCHAR,
                tag VARCHAR,
                type VARCHAR
            ) WITH (
                KAFKA_TOPIC = 'test_topic_json',
                VALUE_FORMAT = 'JSON',
                PARTITIONS = 1
            );
        """)

        self.assertIn(self.stream_name.upper(), self.ksql.streams(), "Stream was not created as expected")

        # 2. Insert rows
        rows = [
            {
                "ASSET_UUID": "uuid-001",
                "ID": "sensor-A",
                "VALUE": "42.5",
                "TAG": "temperature",
                "TYPE": "Samples"
            },
            {
                "ASSET_UUID": "uuid-002",
                "ID": "sensor-B",
                "VALUE": "101.3",
                "TAG": "pressure",
                "TYPE": "Samples"
            }
        ]
        response = self.ksql.insert_into_stream(self.stream_name, rows)
        self.assertEqual(len(response), 2)
        self.assertTrue(all("status" in r for r in response))

        # 3. Query the stream (wait briefly to ensure inserts are committed)
        time.sleep(1)

        query = f"""
            SELECT ASSET_UUID, id, value, tag, type
            FROM {self.stream_name};
        """
        df = self.ksql.query(query)
        self.assertEqual(len(df), 2)
        self.assertIn("ASSET_UUID", df.columns)
        self.assertIn("ID", df.columns)

        expected_df = pd.DataFrame(rows)

        # Sorting both by ASSET_UUID for comparison
        df_sorted = df.sort_values(by="ASSET_UUID").reset_index(drop=True)
        expected_df_sorted = expected_df.sort_values(by="ASSET_UUID").reset_index(drop=True)

        pd.testing.assert_frame_equal(df_sorted, expected_df_sorted, check_dtype=False)
