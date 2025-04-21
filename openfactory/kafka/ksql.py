import json
import pandas as pd
import time
import atexit
import signal
import logging
import httpx
from urllib.parse import urljoin
from openfactory.setup_logging import configure_prefixed_logger, setup_third_party_loggers


class KSQLDBClientException(Exception):
    """ A general error in OpenFactory """
    pass


class KSQLDBClient:
    """ ksqlDB client used by OpenFactory """

    def __init__(
        self,
        ksqldb_url: str,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        timeout: float = 10.0,
    ):
        """
        :param ksqldb_url: URL of the ksqlDB server
        :param max_retries: Number of retry attempts on network failure
        :param retry_delay: Seconds to wait between retries
        :param timeout: Request timeout in seconds
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
        self.logger = configure_prefixed_logger("openfactory.ksqlDB", prefix="KSQL")

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
        Internal HTTP request wrapper with retry logic
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
        """ Return server info """
        resp = self._request('GET', 'info')
        return resp.json()

    def get_kafka_topic(self, stream_name: str) -> str:
        """ Return Kafka topic for a stream """
        payload = {"ksql": f"DESCRIBE {stream_name} EXTENDED;"}
        resp = self._request('POST', '/ksql', json_payload=payload)
        data = resp.json()
        try:
            return data[0]['sourceDescription']['topic']
        except (KeyError, IndexError):
            raise KSQLDBClientException("Stream details not found")

    def streams(self) -> list[str]:
        """ List existing streams """
        payload = {"ksql": "SHOW STREAMS;", "streamsProperties": {}}
        resp = self._request('POST', '/ksql', json_payload=payload)
        data = resp.json()
        entry = data[0]
        return [r['name'] for r in entry.get('streams', [])]

    def tables(self) -> list[str]:
        """ List existing tables """
        payload = {"ksql": "SHOW TABLES;", "streamsProperties": {}}
        resp = self._request('POST', '/ksql', json_payload=payload)
        data = resp.json()
        entry = data[0]
        return [r['name'] for r in entry.get('tables', [])]

    def query(self, ksql: str) -> pd.DataFrame:
        """ Execute a pull query and return a DataFrame """
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
        """ Execute a statement query (e.g., CREATE/DROP) """
        payload = {"ksql": sql}
        headers = {"Accept": "application/vnd.ksql.v1+json"}
        resp = self._request('POST', '/ksql', json_payload=payload, headers=headers)
        return resp.json()

    def insert_into_stream(self, stream_name: str, rows: list[dict]) -> list[dict]:
        """ Insert rows into a stream over HTTP/2 """
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
        """ Close HTTP client """
        if self._client:
            self.logger.info("Closing HTTP client")
            self._client.close()
            self._client = None

    def _handle_exit(self, signum, frame) -> None:
        if callable(self.old_sigint) and signum == signal.SIGINT:
            self.old_sigint(signum, frame)
        if callable(self.old_sigterm) and signum == signal.SIGTERM:
            self.old_sigterm(signum, frame)
        self.logger.info("Received termination signal %s, shutting down", signum)
        self.close()
        raise SystemExit

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    ksql = KSQLDBClient('http://localhost:8088')
    print('Info:', ksql.info())
    print('Streams:', ksql.streams())
    print('Tables:', ksql.tables())
    df = ksql.query("SELECT ID, VALUE, TYPE FROM assets WHERE ASSET_UUID='PROVER3018' AND TYPE='Samples';")
    print(df)
    ksql.close()
