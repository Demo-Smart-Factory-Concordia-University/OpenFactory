import unittest
from unittest.mock import patch, MagicMock
import requests
import pandas as pd
import json
import signal
from urllib.parse import urljoin
from openfactory.kafka.ksql import KSQLDBClient, KSQLDBClienException


class TestKSQLDBClient(unittest.TestCase):
    """
    Test KSQLDBClient class
    """

    def setUp(self):
        # Patch signal.getsignal
        self.getsignal_patcher = patch("signal.getsignal", return_value=lambda s, f: None)
        self.mock_getsignal = self.getsignal_patcher.start()

        # Patch builtins.exit so test doesn't exit
        self.exit_patcher = patch("builtins.exit")
        self.mock_exit = self.exit_patcher.start()

        # Setup the client with patched environment
        self.ksqldb_url = "http://some-url:8088/"
        self.client = KSQLDBClient(self.ksqldb_url, max_retries=3, retry_delay=0)

    def tearDown(self):
        self.client.close()
        self.getsignal_patcher.stop()
        self.exit_patcher.stop()

    @patch.object(KSQLDBClient, 'close')
    def test_close_called_on_exit(self, mock_close):
        """ Test KSQLDBClient.close is called when the object goes out of scope """
        def create_client():
            with KSQLDBClient("http://fake-url:8088"):
                pass  # do nothing

        create_client()

        # Assert close was called once upon exiting the with-statement
        mock_close.assert_called_once()

    @patch("requests.Session.get")
    def test_info_success(self, mock_get):
        """ Test info method returns server info on success """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"KsqlServerInfo": {"version": "0.28.0"}}
        mock_get.return_value = mock_response

        result = self.client.info()

        expected_url = urljoin(self.ksqldb_url, "info")
        mock_get.assert_called_once_with(expected_url)
        self.assertEqual(result["KsqlServerInfo"]["version"], "0.28.0")

    @patch.object(KSQLDBClient, "_create_session")
    @patch("requests.Session.get")
    def test_info_retries_then_succeeds(self, mock_get, mock_create_session):
        """ Test info method retries on failure and succeeds """
        mock_get.side_effect = [
            requests.ConnectionError("Connection failed"),
            requests.ConnectionError("Connection failed again"),
            MagicMock(status_code=200, json=lambda: {"KsqlServerInfo": {"version": "0.30.0"}})
        ]

        dummy_session = MagicMock()
        dummy_session.get = mock_get
        mock_create_session.return_value = dummy_session

        result = self.client.info()

        self.assertEqual(result["KsqlServerInfo"]["version"], "0.30.0")
        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(mock_create_session.call_count, 2)

    @patch.object(KSQLDBClient, "_create_session")
    @patch("requests.Session.get")
    def test_info_fails_after_max_retries(self, mock_get, mock_create_session):
        """ Test info method raises exception after max retries """
        mock_get.side_effect = requests.ConnectionError("Connection failed")

        dummy_session = MagicMock()
        dummy_session.get = mock_get
        mock_create_session.return_value = dummy_session

        with self.assertRaises(KSQLDBClienException) as context:
            self.client.info()

        self.assertIn("Failed to connect to ksqlDB", str(context.exception))
        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(mock_create_session.call_count, 3)

    @patch("requests.Session.post")
    def test_get_kafka_topic_success(self, mock_post):
        """ Test get_kafka_topic method """
        stream_name = "my_stream"
        expected_query = f"DESCRIBE {stream_name} EXTENDED;"
        expected_payload = {"ksql": expected_query}
        expected_topic = "test_topic"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"sourceDescription": {"topic": expected_topic}}]
        mock_post.return_value = mock_response

        result = self.client.get_kafka_topic(stream_name)

        self.assertEqual(result, expected_topic)

        # Validate the POST request
        mock_post.assert_called_once()
        url, = mock_post.call_args[0]
        kwargs = mock_post.call_args[1]

        self.assertIn("/ksql", url)
        self.assertEqual(json.loads(kwargs["data"]), expected_payload)
        self.assertFalse(kwargs["stream"])
        self.assertEqual(kwargs["timeout"], 10)

    @patch("requests.Session.post")
    def test_get_kafka_topic_stream_not_found(self, mock_post):
        """ Test get_kafka_topic method when stream does not exist """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{}]
        mock_post.return_value = mock_response

        with self.assertRaises(Exception) as context:
            self.client.get_kafka_topic("missing_stream")

        self.assertIn("Stream details not found", str(context.exception))

    @patch.object(KSQLDBClient, "_create_session")
    @patch("requests.Session.post")
    def test_get_kafka_topic_retries_on_failure(self, mock_post, mock_create_session):
        """ Test get_kafka_topic method with reconnect attempts """
        # Simulate 2 connection errors followed by a success
        fail = requests.ConnectionError("mock_fail")
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = [{"sourceDescription": {"topic": "retry_topic"}}]
        mock_post.side_effect = [fail, fail, success_response]

        # Patch session and ensure post calls go to mock_post
        dummy_session = MagicMock()
        dummy_session.post = mock_post
        mock_create_session.return_value = dummy_session

        result = self.client.get_kafka_topic("retry_stream")

        self.assertEqual(result, "retry_topic")
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(mock_create_session.call_count, 2)

    @patch.object(KSQLDBClient, "_create_session")
    @patch("requests.Session.post")
    def test_get_kafka_topic_fails_after_max_retries(self, mock_post, mock_create_session):
        """ Test get_kafka_topic raises exception after exceeding max_retries """
        # Always fail with connection error
        mock_post.side_effect = requests.ConnectionError("fail")

        # Create dummy session with mocked post method
        dummy_session = MagicMock()
        dummy_session.post = mock_post
        mock_create_session.return_value = dummy_session

        with self.assertRaises(Exception) as context:
            self.client.get_kafka_topic("dead_stream")

        self.assertIn("Failed to connect to ksqlDB", str(context.exception))
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(mock_create_session.call_count, 3)

    @patch("requests.Session.post")
    def test_streams_success(self, mock_post):
        """ Test streams method returns list of stream names """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            "statementText": "SHOW STREAMS;",
            "streams": [
                {"name": "stream_one"},
                {"name": "stream_two"}
            ]
        }]
        mock_post.return_value = mock_response

        result = self.client.streams()
        self.assertEqual(result, ["stream_one", "stream_two"])

        # Ensure correct endpoint and payload used
        url = urljoin(self.ksqldb_url, "/ksql")
        expected_payload = {"ksql": "SHOW STREAMS;", "streamsProperties": {}}
        mock_post.assert_called_once_with(
            url,
            data=json.dumps(expected_payload),
            stream=False,
            timeout=10
        )

    @patch("requests.Session.post")
    def test_streams_empty_list_if_no_streams_key(self, mock_post):
        """ Test streams returns empty list when no 'streams' key exists """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{}]
        mock_post.return_value = mock_response

        result = self.client.streams()
        self.assertEqual(result, [])

    @patch("requests.Session.post")
    def test_streams_returns_empty_on_unexpected_response(self, mock_post):
        """ Test streams returns empty list when response format is unexpected """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"statementText": "SOME OTHER QUERY"}]
        mock_post.return_value = mock_response

        result = self.client.streams()
        self.assertEqual(result, [])

    @patch.object(KSQLDBClient, "_create_session")
    @patch("requests.Session.post")
    def test_streams_retries_on_failure(self, mock_post, mock_create_session):
        """ Test streams method retries and eventually succeeds """
        fail = requests.ConnectionError("fail")
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = [{
            "statementText": "SHOW STREAMS;",
            "streams": [{"name": "stream_ok"}]
        }]

        mock_post.side_effect = [fail, fail, success_response]

        dummy_session = MagicMock()
        dummy_session.post = mock_post
        mock_create_session.return_value = dummy_session

        result = self.client.streams()
        self.assertEqual(result, ["stream_ok"])
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(mock_create_session.call_count, 2)

    @patch.object(KSQLDBClient, "_create_session")
    @patch("requests.Session.post")
    def test_streams_fails_after_max_retries(self, mock_post, mock_create_session):
        """ Test streams raises exception after retries exhausted """
        mock_post.side_effect = requests.Timeout("timeout")

        dummy_session = MagicMock()
        dummy_session.post = mock_post
        mock_create_session.return_value = dummy_session

        with self.assertRaises(Exception) as context:
            self.client.streams()

        self.assertIn("Failed to connect to ksqlDB", str(context.exception))
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(mock_create_session.call_count, 3)

    @patch("requests.Session.post")
    def test_tables_success(self, mock_post):
        """ Test tables method returns list of table names """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            "statementText": "SHOW TABLES;",
            "tables": [
                {"name": "table_one"},
                {"name": "table_two"}
            ]
        }]
        mock_post.return_value = mock_response

        result = self.client.tables()
        self.assertEqual(result, ["table_one", "table_two"])

        # Ensure correct endpoint and payload used
        url = urljoin(self.ksqldb_url, "/ksql")
        expected_payload = {"ksql": "SHOW TABLES;", "streamsProperties": {}}
        mock_post.assert_called_once_with(
            url,
            data=json.dumps(expected_payload),
            stream=False,
            timeout=10
        )

    @patch("requests.Session.post")
    def test_tables_empty_list_if_no_tables_key(self, mock_post):
        """ Test tables returns empty list when no 'tables' key exists """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{}]
        mock_post.return_value = mock_response

        result = self.client.tables()
        self.assertEqual(result, [])

    @patch("requests.Session.post")
    def test_tables_returns_empty_on_unexpected_response(self, mock_post):
        """ Test tables returns empty list when response format is unexpected """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"statementText": "SOME OTHER QUERY"}]
        mock_post.return_value = mock_response

        result = self.client.tables()
        self.assertEqual(result, [])

    @patch.object(KSQLDBClient, "_create_session")
    @patch("requests.Session.post")
    def test_tables_retries_on_failure(self, mock_post, mock_create_session):
        """ Test tables method retries and eventually succeeds """
        fail = requests.ConnectionError("fail")
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = [{
            "statementText": "SHOW TABLES;",
            "tables": [{"name": "table_ok"}]
        }]

        mock_post.side_effect = [fail, fail, success_response]

        dummy_session = MagicMock()
        dummy_session.post = mock_post
        mock_create_session.return_value = dummy_session

        result = self.client.tables()
        self.assertEqual(result, ["table_ok"])
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(mock_create_session.call_count, 2)

    @patch.object(KSQLDBClient, "_create_session")
    @patch("requests.Session.post")
    def test_tables_fails_after_max_retries(self, mock_post, mock_create_session):
        """ Test tables raises exception after retries exhausted """
        mock_post.side_effect = requests.Timeout("timeout")

        dummy_session = MagicMock()
        dummy_session.post = mock_post
        mock_create_session.return_value = dummy_session

        with self.assertRaises(Exception) as context:
            self.client.tables()

        self.assertIn("Failed to connect to ksqlDB", str(context.exception))
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(mock_create_session.call_count, 3)

    @patch("requests.Session.post")
    def test_query(self, mock_post):
        """ Test query method """
        query = "SELECT * FROM test;"
        lines = [
            b'{"columnNames": ["id", "value"]}',
            b'[1, "a"]',
            b'[2, "b"]'
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = iter(lines)
        mock_post.return_value = mock_response

        df = self.client.query(query)

        expected_df = pd.DataFrame([[1, "a"], [2, "b"]], columns=["id", "value"])
        pd.testing.assert_frame_equal(df, expected_df)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("/query", args[0])
        self.assertIn("ksql", kwargs["data"])
        self.assertEqual(json.loads(kwargs["data"])["ksql"], query)

    @patch.object(KSQLDBClient, "_create_session")
    @patch("requests.Session.post")
    def test_query_retries_on_timeout_then_succeeds(self, mock_post, mock_create_session):
        """ Test query method retries on timeout and succeeds on 3rd attempt """
        fail = requests.Timeout("timeout")
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.iter_lines.return_value = iter([
            b'{"columnNames": ["x"]}',
            b'[42]'
        ])

        mock_post.side_effect = [fail, fail, success_response]

        # Patch session to ensure post calls go to mock_post
        dummy_session = MagicMock()
        dummy_session.post = mock_post
        mock_create_session.return_value = dummy_session

        df = self.client.query("SELECT x FROM test;")
        self.assertEqual(df.iloc[0]["x"], 42)
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(mock_create_session.call_count, 2)

    @patch.object(KSQLDBClient, "_create_session")
    @patch("requests.Session.post")
    def test_query_fails_after_max_retries(self, mock_post, mock_create_session):
        """ Test query method raises exception after exceeding max retries """
        # Simulate connection errors (timeouts, etc.) that will cause retries
        mock_post.side_effect = requests.Timeout("timeout")

        # Create a dummy session to mock post method
        dummy_session = MagicMock()
        dummy_session.post = mock_post
        mock_create_session.return_value = dummy_session

        with self.assertRaises(Exception) as context:
            self.client.query("SELECT x FROM test;")

        self.assertIn("Failed to connect to ksqlDB", str(context.exception))
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(mock_create_session.call_count, 3)

    @patch("requests.Session.post")
    def test_query_raises_exception_on_non_200(self, mock_post):
        """ Test query raises excpettion on none 200 response status code """
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with self.assertRaises(Exception) as context:
            self.client.query("SELECT * FROM error_stream;")

        self.assertIn("Error in ksqlDB query", str(context.exception))

    @patch("requests.Session.post")
    def test_statement_query_success(self, mock_post):
        """ Test statement_query method returns response on success """
        statement = "CREATE STREAM test_stream AS SELECT * FROM source_stream;"
        expected_payload = {"ksql": statement}
        expected_headers = {"Accept": "application/vnd.ksql.v1+json"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = self.client.statement_query(statement)

        self.assertEqual(result, mock_response)

        # Validate the POST request
        mock_post.assert_called_once()
        url, = mock_post.call_args[0]
        kwargs = mock_post.call_args[1]

        self.assertIn("/ksql", url)
        self.assertEqual(kwargs["json"], expected_payload)
        self.assertEqual(kwargs["headers"], expected_headers)

    @patch.object(KSQLDBClient, "_create_session")
    @patch("requests.Session.post")
    def test_statement_query_retries_on_failure(self, mock_post, mock_create_session):
        """ Test statement_query method retries on failure and succeeds """
        statement = "CREATE STREAM test_stream AS SELECT * FROM source_stream;"
        fail = requests.ConnectionError("mock_fail")
        success_response = MagicMock()
        success_response.status_code = 200
        mock_post.side_effect = [fail, fail, success_response]

        dummy_session = MagicMock()
        dummy_session.post = mock_post
        mock_create_session.return_value = dummy_session

        result = self.client.statement_query(statement)

        self.assertEqual(result, success_response)
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(mock_create_session.call_count, 2)

    @patch.object(KSQLDBClient, "_create_session")
    @patch("requests.Session.post")
    def test_statement_query_fails_after_max_retries(self, mock_post, mock_create_session):
        """ Test statement_query raises exception after exceeding max retries """
        statement = "CREATE STREAM test_stream AS SELECT * FROM source_stream;"
        mock_post.side_effect = requests.ConnectionError("mock_fail")

        dummy_session = MagicMock()
        dummy_session.post = mock_post
        mock_create_session.return_value = dummy_session

        with self.assertRaises(KSQLDBClienException) as context:
            self.client.statement_query(statement)

        self.assertIn("Failed to connect to ksqlDB", str(context.exception))
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(mock_create_session.call_count, 3)

    @patch("requests.Session.post")
    def test_statement_query_raises_exception_on_non_200(self, mock_post):
        """ Test statement_query raises exception on non-200 response """
        statement = "CREATE STREAM test_stream AS SELECT * FROM source_stream;"
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_post.return_value = mock_response

        with self.assertRaises(requests.HTTPError):
            self.client.statement_query(statement)

    @patch.object(KSQLDBClient, "close")
    def test_handle_exit_on_sigint(self, mock_close):
        """ Test _handle_exit for SIGINT """
        self.client._handle_exit(signal.SIGINT, None)
        mock_close.assert_called_once()
        self.mock_exit.assert_called_once_with(0)

    @patch.object(KSQLDBClient, "close")
    def test_handle_exit_on_sigterm(self, mock_close):
        """ Test _handle_exit for SIGTERM """
        self.client._handle_exit(signal.SIGTERM, None)
        mock_close.assert_called_once()
        self.mock_exit.assert_called_once_with(0)

    @patch("signal.signal")
    @patch("atexit.register")
    def test_register_signals_and_atexit(self, mock_atexit_register, mock_signal_signal):
        """ Test signals SIGINT, SIGTERM and atexit are registred correctly """
        client = KSQLDBClient(self.ksqldb_url)

        # atexit should be registered
        mock_atexit_register.assert_called_once_with(client.close)

        # signal handlers should be set for SIGINT and SIGTERM
        mock_signal_signal.assert_any_call(signal.SIGINT, client._handle_exit)
        mock_signal_signal.assert_any_call(signal.SIGTERM, client._handle_exit)

        client.close()

    @patch("signal.signal")
    @patch("atexit.register")
    def test_stores_old_signal_handlers(self, mock_atexit_register, mock_signal_signal):
        """ Test old signal handlers are stored """
        # Set up dummy return values for getsignal
        mock_old_sigint = MagicMock()
        mock_old_sigterm = MagicMock()
        self.mock_getsignal.side_effect = [mock_old_sigint, mock_old_sigterm]

        client = KSQLDBClient(self.ksqldb_url)

        # Ensure getsignal is called for both SIGINT and SIGTERM
        self.mock_getsignal.assert_any_call(signal.SIGINT)
        self.mock_getsignal.assert_any_call(signal.SIGTERM)

        # Ensure the old handlers are stored correctly
        self.assertEqual(client.old_sigint_handler, mock_old_sigint)
        self.assertEqual(client.old_sigterm_handler, mock_old_sigterm)

        client.close()

    @patch("httpx.Client.stream")
    def test_insert_into_stream_success(self, mock_stream):
        """ Test insert_into_stream method on success """
        stream_name = "test_stream"
        rows = [
            {"field1": "foo", "field2": 123, "field3": True},
            {"field1": "bar", "field2": 456, "field3": False},
        ]
        expected_url = urljoin(self.ksqldb_url, "/inserts-stream")
        expected_data = (
            json.dumps({"target": stream_name})
            + "\n"
            + "\n".join(json.dumps(row) for row in rows)
            + "\n"
        )
        expected_headers = {"Content-Type": "application/vnd.ksql.v1+json"}

        # Setup fake response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_bytes.return_value = iter([
            b'{"status":"success"}\n',
            b'{"status":"success"}\n'
        ])
        mock_stream.return_value.__enter__.return_value = mock_response

        # Call method
        result = self.client.insert_into_stream(stream_name, rows)

        self.assertEqual(result, [{"status": "success"}, {"status": "success"}])
        mock_stream.assert_called_once()

        # Inspect the actual arguments passed
        called_args, called_kwargs = mock_stream.call_args

        self.assertEqual(called_args[0], "POST")
        self.assertEqual(called_args[1], expected_url)
        self.assertEqual(called_kwargs["content"], expected_data)
        self.assertEqual(called_kwargs["headers"], expected_headers)

    @patch("httpx.Client.stream")
    def test_insert_into_stream_failure(self, mock_stream):
        """ Test insert_into_stream method raises exception on failure """
        stream_name = "test_stream"
        rows = [
            {"field1": "foo", "field2": 123, "field3": True},
            {"field1": "bar", "field2": 456, "field3": False},
        ]

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.iter_bytes.return_value = iter([b'{"error":"failure"}\n'])
        mock_stream.return_value.__enter__.return_value = mock_response

        with self.assertRaises(KSQLDBClienException) as context:
            self.client.insert_into_stream(stream_name, rows)

        self.assertIn("Error in ksqlDB insert", str(context.exception))
