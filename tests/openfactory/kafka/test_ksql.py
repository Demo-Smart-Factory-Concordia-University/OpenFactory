import unittest
from unittest.mock import patch, MagicMock
import httpx
import pandas as pd
import json
import signal
from openfactory.kafka.ksql import KSQLDBClient, KSQLDBClientException


class TestKSQLDBClient(unittest.TestCase):
    """
    Test KSQLDBClient class
    """
    def setUp(self):
        self.ksqldb_url = "http://localhost:8088"
        self.client = KSQLDBClient(self.ksqldb_url)

    def tearDown(self):
        self.client.close()

    @patch("openfactory.kafka.ksql.configure_prefixed_logger")
    @patch("openfactory.kafka.ksql.setup_third_party_loggers")
    def test_logger_setup(self, mock_setup_loggers, mock_configure_logger):
        """ Test logger setup in KSQLDBClient """

        # Mock logger returned by configure_prefixed_logger
        mock_logger = MagicMock()
        mock_configure_logger.return_value = mock_logger

        # Mock the actual creation of the KSQLDBClient
        ksqldb_url = "http://localhost:8088"
        KSQLDBClient(ksqldb_url)

        # Assertions to ensure the logger was correctly set up
        mock_setup_loggers.assert_called_once()
        mock_configure_logger.assert_called_once_with("openfactory.ksqlDB", prefix="KSQL")
        mock_logger.info.assert_called_once_with(f"Connected to ksqlDB at {ksqldb_url}")

    @patch("openfactory.kafka.ksql.KSQLDBClient._request")
    def test_info_success(self, mock_request):
        """ Test info method of KSQLDBClient """

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"KsqlServerInfo": {"version": "0.28.0"}}
        mock_request.return_value = mock_response

        # Call the method
        result = self.client.info()

        # Assertions
        self.assertEqual(result["KsqlServerInfo"]["version"], "0.28.0")
        mock_request.assert_called_once_with("GET", "info")

    @patch("openfactory.kafka.ksql.KSQLDBClient._request")
    def test_get_kafka_topic_success(self, mock_request):
        """ Test get_kafka_topic method of KSQLDBClient """
        stream_name = "test_stream"

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"sourceDescription": {"topic": "test_topic"}}]
        mock_request.return_value = mock_response

        # Call the method
        result = self.client.get_kafka_topic(stream_name)

        # Assertions
        self.assertEqual(result, "test_topic")
        mock_request.assert_called_once_with(
            "POST",
            "/ksql",
            json_payload={"ksql": f"DESCRIBE {stream_name} EXTENDED;"}
        )

    @patch("httpx.Client.request")
    def test_get_kafka_topic_not_found(self, mock_request):
        """ Test get_kafka_topic method of KSQLDBClient when stream is not found """
        stream_name = "missing_stream"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{}]
        mock_request.return_value = mock_response

        with self.assertRaises(KSQLDBClientException):
            self.client.get_kafka_topic(stream_name)

    @patch("openfactory.kafka.ksql.KSQLDBClient._request")
    def test_streams_success(self, mock_request):
        """ Test streams method of KSQLDBClient """
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"streams": [{"name": "stream1"}, {"name": "stream2"}]}
        ]
        mock_request.return_value = mock_response

        # Call method
        result = self.client.streams()

        # Assertions
        self.assertEqual(result, ["stream1", "stream2"])
        mock_request.assert_called_once_with(
            "POST",
            "/ksql",
            json_payload={
                "ksql": "SHOW STREAMS;",
                "streamsProperties": {}
            }
        )

    @patch("openfactory.kafka.ksql.KSQLDBClient._request")
    def test_tables_success(self, mock_request):
        """ Test tables method of KSQLDBClient """
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"tables": [{"name": "table1"}, {"name": "table2"}]}
        ]
        mock_request.return_value = mock_response

        # Call method
        result = self.client.tables()

        # Assertions
        self.assertEqual(result, ["table1", "table2"])
        mock_request.assert_called_once_with(
            "POST",
            "/ksql",
            json_payload={
                "ksql": "SHOW TABLES;",
                "streamsProperties": {}
            }
        )

    @patch("openfactory.kafka.ksql.KSQLDBClient._request")
    def test_query_success(self, mock_request):
        """ Test query method of KSQLDBClient """
        query = "SELECT * FROM test_table;"

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.read.return_value = (
            b'{"columnNames":["id","value"]}\n[1,"a"]\n[2,"b"]\n'
        )

        # Mock context manager return
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_response
        mock_request.return_value = mock_context

        # Call method
        result = self.client.query(query)

        # Assert result
        expected_df = pd.DataFrame([[1, "a"], [2, "b"]], columns=["id", "value"])
        pd.testing.assert_frame_equal(result, expected_df)

        mock_request.assert_called_once_with(
            "POST",
            "/query",
            json_payload={"ksql": query, "streamsProperties": {}},
            stream=True
        )

    @patch("openfactory.kafka.ksql.KSQLDBClient._request")
    def test_statement_query_success(self, mock_request):
        """ Test statement_query method of KSQLDBClient """
        sql = "CREATE STREAM test_stream AS SELECT * FROM source_stream;"

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_request.return_value = mock_response

        # Call the method
        result = self.client.statement_query(sql)

        # Assertions
        self.assertEqual(result, {"status": "success"})
        mock_request.assert_called_once_with(
            "POST",
            "/ksql",
            json_payload={"ksql": sql},
            headers={'Accept': 'application/vnd.ksql.v1+json'}
        )

    @patch("openfactory.kafka.ksql.KSQLDBClient._request")
    def test_insert_into_stream_success(self, mock_request):
        """ Test insert_into_stream method of KSQLDBClient """
        stream_name = "test_stream"
        rows = [{"field1": "value1"}, {"field1": "value2"}]

        # Simulate streaming response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_bytes.return_value = iter([
            b'{"status":"success"}\n', b'{"status":"success"}\n'
        ])
        mock_request.return_value.__enter__.return_value = mock_response

        # Call the method
        result = self.client.insert_into_stream(stream_name, rows)

        # Construct expected request content
        expected_lines = [
            json.dumps({"target": stream_name}).encode() + b"\n"
        ] + [json.dumps(row).encode() + b"\n" for row in rows]
        expected_content = b"".join(expected_lines)

        # Assertions
        self.assertEqual(result, [{"status": "success"}, {"status": "success"}])
        mock_request.assert_called_once_with(
            'POST',
            '/inserts-stream',
            stream=True,
            headers={"Content-Type": "application/vnd.ksql.v1+json"},
            content=expected_content
        )

    @patch("httpx.Client.request")
    def test_request_retries_on_failure(self, mock_request):
        mock_request.side_effect = [httpx.RequestError("Connection failed"), MagicMock(status_code=200)]
        result = self.client.info()
        self.assertIsNotNone(result)
        self.assertEqual(mock_request.call_count, 2)

    @patch("httpx.Client.request")
    def test_request_fails_after_max_retries(self, mock_request):
        mock_request.side_effect = httpx.RequestError("Connection failed")
        with self.assertRaises(KSQLDBClientException):
            self.client.info()
        self.assertEqual(mock_request.call_count, self.client.max_retries)

    @patch("openfactory.kafka.ksql.atexit.register")
    @patch("openfactory.kafka.ksql.signal.signal")
    @patch("openfactory.kafka.ksql.signal.getsignal")
    def test_register_cleanup(self, mock_getsignal, mock_signal, mock_atexit_register):
        """Test _register_cleanup behavior during init"""

        # Setup mock return values for old signal handlers
        mock_getsignal.side_effect = [MagicMock(), MagicMock()]

        # IMPORTANT: new instance created after mocks are applied
        client = KSQLDBClient(self.ksqldb_url)

        # Check that atexit registered the client.close method
        mock_atexit_register.assert_called_once_with(client.close)

        # Check signal handlers were fetched and updated
        mock_getsignal.assert_any_call(signal.SIGINT)
        mock_getsignal.assert_any_call(signal.SIGTERM)
        mock_signal.assert_any_call(signal.SIGINT, client._handle_exit)
        mock_signal.assert_any_call(signal.SIGTERM, client._handle_exit)
