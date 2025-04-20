import requests
import json
import pandas as pd
import time
import atexit
import signal
import httpx
from urllib.parse import urljoin


class KSQLDBClienException(Exception):
    """ A general error in OpenFactory """
    pass


class KSQLDBClient:
    """
    ksqlDB client used by OpenFactory
    """

    def __init__(self, ksqldb_url, max_retries=3, retry_delay=2):
        """
        Initializes the ksqlDB client with a persistent session
        :param ksqldb_url: URL of the ksqlDB server
        :param max_retries: Number of times to retry if the connection fails
        :param retry_delay: Seconds to wait between retries
        """
        self.ksqldb_url = ksqldb_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = self._create_session()
        self._http2_client = httpx.Client(http1=False, http2=True)
        self._register_cleanup()

    def _create_session(self):
        """ Creates a new requests session """
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        return session

    def _register_cleanup(self):
        """ Registers cleanup functions for normal and forced exits """
        # Ensures close() runs at exit
        atexit.register(self.close)

        # Store old signal handlers
        self.old_sigint_handler = signal.getsignal(signal.SIGINT)
        self.old_sigterm_handler = signal.getsignal(signal.SIGTERM)

        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    def info(self):
        """ Return info on ksqlDB server """
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(urljoin(self.ksqldb_url, "info"))
                response.raise_for_status()
                return response.json()

            except (requests.ConnectionError, requests.Timeout) as e:
                print(f"Connection failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                time.sleep(self.retry_delay)
                self.session = self._create_session()

        raise KSQLDBClienException(f"Failed to connect to ksqlDB {self.ksqldb_url} after {self.max_retries} attempts.")

    def get_kafka_topic(self, stream_name) -> str:
        """
        Gets Kafka topic from the ksqlDB stream 'stream_name'

        :param stream_name: Name of the ksqlDB stream
        :return: The Kafka topic name as a string
        :raises KSQLDBClienException: If the query fails or the stream is not found
        """
        query = f"DESCRIBE {stream_name} EXTENDED;"
        payload = {"ksql": query}

        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    urljoin(self.ksqldb_url, "/ksql"),
                    data=json.dumps(payload),
                    stream=False,
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    if "sourceDescription" in data[0]:
                        # Extract and return the Kafka topic
                        return data[0]["sourceDescription"]["topic"]
                    else:
                        raise KSQLDBClienException("Stream details not found in the response.")

                # If response is not OK, raise an KSQLDBClienException
                raise KSQLDBClienException(f"Error in ksqlDB query {query}: {response.text}")

            except (requests.ConnectionError, requests.Timeout) as e:
                print(f"Connection failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                time.sleep(self.retry_delay)
                self.session = self._create_session()  # Reset session before retrying

        raise KSQLDBClienException(f"Failed to connect to ksqlDB after {self.max_retries} attempts.")

    def streams(self):
        """
        Returns a list of existing stream names in ksqlDB
        """
        query = "SHOW STREAMS;"
        payload = {"ksql": query, "streamsProperties": {}}

        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    urljoin(self.ksqldb_url, "/ksql"),
                    data=json.dumps(payload),
                    stream=False,
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    if data and "streams" in data[0]:
                        return [stream["name"] for stream in data[0]["streams"]]
                    elif "statementText" in data[0] and "SHOW STREAMS" in data[0]["statementText"]:
                        return [row["name"] for row in data[0]["streams"]]
                    else:
                        return []
                raise KSQLDBClienException(f"Error retrieving streams: {response.text}")

            except (requests.ConnectionError, requests.Timeout) as e:
                print(f"Connection failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                time.sleep(self.retry_delay)
                self.session = self._create_session()

        raise KSQLDBClienException(f"Failed to connect to ksqlDB after {self.max_retries} attempts.")

    def tables(self):
        """
        Returns a list of existing table names in ksqlDB
        """
        query = "SHOW TABLES;"
        payload = {"ksql": query, "streamsProperties": {}}

        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    urljoin(self.ksqldb_url, "/ksql"),
                    data=json.dumps(payload),
                    stream=False,
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    if data and "tables" in data[0]:
                        return [table["name"] for table in data[0]["tables"]]
                    elif "statementText" in data[0] and "SHOW TABLES" in data[0]["statementText"]:
                        return [row["name"] for row in data[0]["tables"]]
                    else:
                        return []
                raise KSQLDBClienException(f"Error retrieving tables: {response.text}")

            except (requests.ConnectionError, requests.Timeout) as e:
                print(f"Connection failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                time.sleep(self.retry_delay)
                self.session = self._create_session()

        raise KSQLDBClienException(f"Failed to connect to ksqlDB after {self.max_retries} attempts.")

    def query(self, query: str) -> pd.DataFrame:
        """
        Executes a ksqlDB query with automatic retry logic
        :param query: ksqlDB SQL query string
        :return: Pandas DataFrame containing the query results
        """
        payload = {"ksql": query, "streamsProperties": {}}

        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    urljoin(self.ksqldb_url, "/query"),
                    data=json.dumps(payload),
                    stream=True,
                    timeout=10
                )

                if response.status_code == 200:
                    return self._process_response(response)

                # If response is not OK, raise an KSQLDBClienException
                raise KSQLDBClienException(f"Error in ksqlDB query {query}: {response.text}")

            except (requests.ConnectionError, requests.Timeout) as e:
                print(f"Connection failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                time.sleep(self.retry_delay)
                self.session = self._create_session()  # Reset session before retrying

        raise KSQLDBClienException(f"Failed to connect to ksqlDB after {self.max_retries} attempts.")

    def statement_query(self, statement):
        """ Executes a ksqlDB statement query """
        payload = {"ksql": statement}
        headers = {"Accept": "application/vnd.ksql.v1+json"}

        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    urljoin(self.ksqldb_url, "/ksql"),
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                return response

            except requests.exceptions.HTTPError as e:
                error_message = f"HTTPError occurred: {e.response.status_code} - {e.response.reason} - {e.response.text}"
                raise KSQLDBClienException(f"Query failed with error: {error_message}")

            except (requests.ConnectionError, requests.Timeout) as e:
                print(f"Connection failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                time.sleep(self.retry_delay)
                self.session = self._create_session()  # Reset session before retrying

        raise KSQLDBClienException(f"Failed to connect to ksqlDB after {self.max_retries} attempts.")

    def insert_into_stream(self, stream_name, rows):
        """
        Insert rows into a ksqlDB stream.
        :param stream_name: The name of the ksqlDB stream
        :param rows: List of dictionaries representing the rows to insert like so
                     rows = [
                        {"field1": "foo", "field2": 123, "field3": True},
                        {"field1": "bar", "field2": 456, "field3": False},
                     ]
        :return: List of responses from the server
        """
        url = urljoin(self.ksqldb_url, "/inserts-stream")
        data = json.dumps({"target": stream_name}) + "\n"
        for row in rows:
            data += json.dumps(row) + "\n"

        headers = {"Content-Type": "application/vnd.ksql.v1+json"}

        with self._http2_client.stream("POST", url, content=data, headers=headers) as r:
            response_text = b"".join(r.iter_bytes()).decode("utf-8")

            if r.status_code != 200:
                raise KSQLDBClienException(f"Error in ksqlDB insert: {response_text}")

            # Successful: return parsed lines
            return [json.loads(line) for line in response_text.splitlines()]

    def _process_response(self, response):
        """ Processes the ksqlDB response and returns a DataFrame """
        data, columns = [], []

        for line in response.iter_lines():
            if line:
                json_line = json.loads(line.decode("utf-8"))

                if "columnNames" in json_line:
                    columns = json_line["columnNames"]
                elif isinstance(json_line, list):
                    data.append(json_line)

        return pd.DataFrame(data, columns=columns) if data else pd.DataFrame(columns=columns)

    def close(self):
        """ Closes the session """
        if self.session:
            print("Closing ksqlDB connection...")
            self._http2_client.close()
            self.session.close()
            self.session = None  # Avoid re-closing

    def _handle_exit(self, signum, frame):
        """ Handles termination signals (SIGINT/SIGTERM) by closing the session """
        # Call the previous handler if it exists and is not default
        if signum == signal.SIGINT and callable(self.old_sigint_handler):
            self.old_sigint_handler(signum, frame)
        if signum == signal.SIGTERM and callable(self.old_sigterm_handler):
            self.old_sigterm_handler(signum, frame)

        print(f"\nReceived termination signal ({signum}), shutting down ksqlDB connection...")
        self.close()

        exit(0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":

    # Example usage of KSQLDBClient
    ksql = KSQLDBClient('http://localhost:8088')

    print('ksqlDB server info:', ksql.info())
    print('streams:', ksql.streams())
    print('tables:', ksql.tables())

    query = "SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='PROVER3018' AND TYPE='Samples';"
    print('\nSamples:\n', ksql.query(query))

    query = "SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='PROVER3018' AND TYPE='Events';"
    print('\nEvents:\n', ksql.query(query))

    print('\nKafka topic of CMDS_STREAM:', ksql.get_kafka_topic('CMDS_STREAM'), '\n')

    ksql.statement_query("DROP STREAM IF EXISTS demo_stream;")
    ksql.statement_query(
        """
            CREATE STREAM demo_stream (
                ASSET_UUID VARCHAR KEY,
                id VARCHAR,
                value VARCHAR,
                tag VARCHAR,
                type VARCHAR
            ) WITH (
                KAFKA_TOPIC = 'ofa_assets',
                PARTITIONS = 1,
                VALUE_FORMAT = 'JSON'
            );
        """)

    rows = [
        {
            "ASSET_UUID": "123e4567-e89b-12d3-a456-426614174000",
            "id": "sensor-1",
            "value": "72.4",
            "tag": "temperature",
            "type": "float"
        },
        {
            "ASSET_UUID": "987e6543-e21b-12d3-a456-426614174999",
            "id": "sensor-2",
            "value": "1013",
            "tag": "pressure",
            "type": "int"
        }
    ]

    response = ksql.insert_into_stream("demo_stream", rows)
    for entry in response:
        print(entry)

    ksql.statement_query("DROP STREAM IF EXISTS demo_stream;")

    ksql.close()
