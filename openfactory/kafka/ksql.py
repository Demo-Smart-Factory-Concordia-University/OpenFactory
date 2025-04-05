import requests
import json
import pandas as pd
import time
import atexit
import signal
from urllib.parse import urljoin


class KSQLDBClient:
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
                self.session = self._create_session()  # Reset session before retrying

    def get_kafka_topic(self, stream_name) -> str:
        """
        Gets Kafka topic from the ksqlDB stream 'stream_name'

        :param stream_name: Name of the ksqlDB stream
        :return: The Kafka topic name as a string
        :raises Exception: If the query fails or the stream is not found
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
                        raise Exception("Stream details not found in the response.")

                # If response is not OK, raise an exception
                raise Exception(f"Error in ksqlDB query {query}: {response.text}")

            except (requests.ConnectionError, requests.Timeout) as e:
                print(f"Connection failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                time.sleep(self.retry_delay)
                self.session = self._create_session()  # Reset session before retrying

        raise Exception(f"Failed to connect to ksqlDB after {self.max_retries} attempts.")

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

                # If response is not OK, raise an exception
                raise Exception(f"Error in ksqlDB query {query}: {response.text}")

            except (requests.ConnectionError, requests.Timeout) as e:
                print(f"Connection failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                time.sleep(self.retry_delay)
                self.session = self._create_session()  # Reset session before retrying

        raise Exception(f"Failed to connect to ksqlDB after {self.max_retries} attempts.")

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

    query = "SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='PROVER3018' AND TYPE='Samples';"
    print('\nSamples:\n', ksql.query(query))

    query = "SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='PROVER3018' AND TYPE='Events';"
    print('\nEvents:\n', ksql.query(query))

    print('\nKafka topic of CMDS_STREAM:', ksql.get_kafka_topic('CMDS_STREAM'), '\n')

    ksql.close()
