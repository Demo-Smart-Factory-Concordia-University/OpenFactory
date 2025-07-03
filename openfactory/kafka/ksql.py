""" OpenFactory ksqlDB client. """

import json
import pandas as pd
import time
import atexit
import signal
import httpx
from urllib.parse import urljoin
from openfactory.setup_logging import configure_prefixed_logger, setup_third_party_loggers
import openfactory.config as Config


class KSQLDBClientException(Exception):
    """ A general error in OpenFactory. """
    pass


class KSQLDBClient:
    """
    ksqlDB client used by OpenFactory.

    Example usage:
        .. code-block:: python

            from openfactory.kafka import KSQLDBClient

            ksql = KSQLDBClient('http://localhost:8088')
            print('Info:   ', ksql.info())
            print('Streams:', ksql.streams())
            print('Tables: ', ksql.tables())
            df = ksql.query("SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='PROVER3018' AND TYPE='Samples';")
            print(df)
            ksql.close()
    """

    def __init__(
        self,
        ksqldb_url: str,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        timeout: float = 10.0,
        loglevel: str = Config.KSQLDB_LOG_LEVEL,
    ):
        """
        Initialize the KSQLDB client.

        Args:
            ksqldb_url (str): URL of the ksqlDB server.
            max_retries (int): Number of retry attempts on network failure. Defaults to 3.
            retry_delay (float): Seconds to wait between retries. Defaults to 2.0.
            timeout (float): Request timeout in seconds. Defaults to 10.0.
            loglevel (str): Logging level for the client. Defaults to Config.KSQLDB_LOG_LEVEL.
        """
        self.ksqldb_url = ksqldb_url.rstrip("/")
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = httpx.Timeout(timeout)

        # single HTTP/2-only client
        self._client = httpx.Client(
            headers={"Content-Type": "application/json"},
            http2=True,
            http1=False,
            timeout=self.timeout,
        )

        self._register_cleanup()

        # Set up logging
        setup_third_party_loggers()
        self.logger = configure_prefixed_logger(
            "openfactory.ksqlDB",
            prefix="KSQL",
            level=loglevel)

        self.logger.info(f"Connected to ksqlDB at {self.ksqldb_url}")

    def _register_cleanup(self) -> None:
        atexit.register(self.close)
        self.old_sigint = signal.getsignal(signal.SIGINT)
        self.old_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    def _request(
        self,
        method: str,
        path: str,
        json_payload: dict = None,
        stream: bool = False,
        headers: dict = None,
        content: bytes = None,
    ) -> httpx.Response:
        """
        Internal HTTP request wrapper with retry logic.

        Args:
            method (str): HTTP method to use (e.g., "GET", "POST").
            path (str): Endpoint path to be appended to the base URL.
            json_payload (dict): JSON data to send in the request body. Defaults to None.
            stream (bool): Whether to use streaming for the response. Defaults to False.
            headers (dict): Optional headers to include in the request. Defaults to None.
            content (bytes): Raw byte content to send in the request body. Defaults to None.

        Returns:
            httpx.Response: The HTTP response object.

        Raises:
            KSQLDBClientException: If all retry attempts fail due to request or HTTP status errors.
        """
        url = urljoin(self.ksqldb_url + '/', path.lstrip('/'))
        for attempt in range(1, self.max_retries + 1):
            try:
                if stream:
                    return self._client.stream(
                        method,
                        url,
                        headers=headers,
                        content=content or json.dumps(json_payload)
                    )
                response = self._client.request(
                    method,
                    url,
                    headers=headers,
                    json=json_payload,
                    content=content
                )
                response.raise_for_status()
                return response

            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                self.logger.warning(
                    "Request %s %s failed (attempt %d/%d): %s",
                    method, url, attempt, self.max_retries, e,
                )
                if attempt == self.max_retries:
                    raise KSQLDBClientException(f"Failed {method} {url}: {e}")
                time.sleep(self.retry_delay)

    def info(self) -> dict:
        """
        Retrieve server information.

        Returns:
            dict: A dictionary containing server information.
        """
        resp = self._request('GET', 'info')
        return resp.json()

    def get_kafka_topic(self, stream_name: str) -> str:
        """
        Retrieve the Kafka topic associated with a KSQL stream.

        Args:
            stream_name (str): The name of the KSQL stream.

        Returns:
            str: The Kafka topic name associated with the stream.

        Raises:
            KSQLDBClientException: If the topic cannot be found in the response.
        """
        payload = {"ksql": f"DESCRIBE {stream_name} EXTENDED;"}
        resp = self._request('POST', '/ksql', json_payload=payload)
        data = resp.json()
        try:
            return data[0]['sourceDescription']['topic']
        except (KeyError, IndexError):
            raise KSQLDBClientException("Stream details not found")

    def streams(self) -> list[str]:
        """
        List existing KSQL streams.

        Returns:
            list[str]: A list of stream names currently defined in KSQLDB.
        """
        payload = {"ksql": "SHOW STREAMS;", "streamsProperties": {}}
        resp = self._request('POST', '/ksql', json_payload=payload)
        data = resp.json()
        entry = data[0]
        return [r['name'] for r in entry.get('streams', [])]

    def tables(self) -> list[str]:
        """
        List existing KSQL tables.

        Returns:
            list[str]: A list of table names currently defined in KSQLDB.
        """
        payload = {"ksql": "SHOW TABLES;", "streamsProperties": {}}
        resp = self._request('POST', '/ksql', json_payload=payload)
        data = resp.json()
        entry = data[0]
        return [r['name'] for r in entry.get('tables', [])]

    def query(self, ksql: str) -> pd.DataFrame:
        """
        Execute a KSQL pull query and return the results as a DataFrame.

        Args:
            ksql (str): The KSQL pull query string to execute.

        Returns:
            pandas.DataFrame: A DataFrame containing the query result rows and columns.

        Raises:
            KSQLDBClientException: If the server returns a non-200 or malformed response.
        """
        payload = {"ksql": ksql, "streamsProperties": {}}
        with self._request('POST', '/query', json_payload=payload, stream=True) as resp:
            raw = resp.read()
        text = raw.decode(errors='ignore')
        if resp.status_code != 200:
            raise KSQLDBClientException(f"Query error: {text}")

        rows = []
        cols = []
        for line in text.splitlines():
            j = json.loads(line)
            if 'columnNames' in j:
                cols = j['columnNames']
            elif isinstance(j, list):
                rows.append(j)
        return pd.DataFrame(rows, columns=cols)

    def statement_query(self, sql: str) -> dict:
        """
        Execute a KSQL statement query (e.g., CREATE, DROP).

        Sends a KSQL statement to the server, typically for DDL or DML operations
        such as creating or dropping streams or tables.

        Args:
            sql (str): The KSQL statement to execute.

        Returns:
            dict: The JSON response from the server as a dictionary.

        Raises:
            KSQLDBClientException: If the request fails or returns an error status.
        """
        payload = {"ksql": sql}
        headers = {"Accept": "application/vnd.ksql.v1+json"}
        return self._request('POST', '/ksql', json_payload=payload, headers=headers)

    def insert_into_stream(self, stream_name: str, rows: list[dict]) -> list[dict]:
        """
        Insert rows into a stream over HTTP/2.

        Args:
            stream_name (str): The name of the KSQL stream to insert data into.
            rows (list[dict]): A list of dictionaries representing the rows to be inserted.

        Returns:
            list[dict]: A list of dictionaries containing the response from the insert operation.

        Raises:
            KSQLDBClientException: If the request fails or returns an error status.
        """
        urlpath = '/inserts-stream'
        content = b"".join(
            [json.dumps({"target": stream_name}).encode() + b"\n"] +
            [json.dumps(r).encode() + b"\n" for r in rows]
        )
        headers = {"Content-Type": "application/vnd.ksql.v1+json"}
        with self._request('POST', urlpath, stream=True, headers=headers, content=content) as resp:
            text = b"".join(resp.iter_bytes()).decode(errors='ignore')
        if resp.status_code != 200:
            raise KSQLDBClientException(f"Insert error: {text}")
        return [json.loads(line) for line in text.splitlines()]

    def close(self) -> None:
        """ Close HTTP client. """
        if self._client:
            self.logger.info("Closing HTTP client")
            self._client.close()
            self._client = None

    def _handle_exit(self, signum, frame) -> None:
        """
        Handle termination signals and perform cleanup.

        This method is called when the process receives termination signals (SIGINT and SIGTERM).
        It attempts to restore the previous signal handlers, logs the termination signal, performs
        any necessary cleanup (e.g., closing resources), and then raises a `SystemExit` to terminate
        the program.

        Args:
            signum (int): The signal number (e.g., SIGINT or SIGTERM).
            frame (signal.Frame): The current stack frame when the signal was received.

        Raises:
            SystemExit: Always raises `SystemExit` after handling the termination signal.
        """
        if callable(self.old_sigint) and signum == signal.SIGINT:
            self.old_sigint(signum, frame)
        if callable(self.old_sigterm) and signum == signal.SIGTERM:
            self.old_sigterm(signum, frame)
        self.logger.info("Received termination signal %s, shutting down", signum)
        self.close()
        raise SystemExit

    def __enter__(self):
        """
        Initialize resources when entering a context manager.

        This method is part of the context management protocol and is called when
        entering the `with` block. It prepares the necessary resources and returns
        the object that will be used within the `with` block.

        Returns:
            self: The instance of the class, typically used within the `with` block.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Clean up resources when exiting a context manager.

        This method is part of the context management protocol and is called when
        exiting the `with` block. It ensures that any necessary cleanup is performed,
        such as closing resources.

        Args:
            exc_type (type): The exception type, if an exception was raised.
            exc_val (BaseException): The exception instance, if an exception was raised.
            exc_tb (traceback): The traceback object, if an exception was raised.
        """
        self.close()


if __name__ == "__main__":
    # Example usage
    ksql = KSQLDBClient('http://localhost:8088')
    print('Info:', ksql.info())
    print('Streams:', ksql.streams())
    print('Tables:', ksql.tables())
    df = ksql.query("SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='PROVER3018' AND TYPE='Samples';")
    print(df)
    ksql.close()
