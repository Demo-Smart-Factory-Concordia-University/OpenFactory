import time
from openfactory.kafka import KSQLDBClient


def wait_for_streams_and_tables(client, expected_streams, expected_tables, check_interval=1):
    """
    Wait until all expected streams and tables exist in ksqlDB.

    :param client: Instance of KSQLDBClient
    :param expected_streams: List of expected stream names
    :param expected_tables: List of expected table names
    :param check_interval: Time in seconds between retries
    """
    while True:
        try:
            current_streams = client.streams()
            current_tables = client.tables()

            missing_streams = [s for s in expected_streams if s not in current_streams]
            missing_tables = [t for t in expected_tables if t not in current_tables]

            if not missing_streams and not missing_tables:
                print("All required streams and tables are present.")
                break

            print("Waiting for missing resources...")

        except Exception as e:
            print(f"Error while checking streams/tables: {e}")
            exit(1)

        time.sleep(check_interval)


expected_streams = [
    'KSQL_PROCESSING_LOG', 'ASSETS_STREAM', 'DOCKER_SERVICES_STREAM', 'CMDS_STREAM',
    'ASSETS_TYPE_STREAM', 'ENRICHED_ASSETS_STREAM', 'ASSETS_AVAIL_STREAM',
    'ASSETS_TYPE_TOMBSTONES', 'ASSETS_AVAIL_TOMBSTONES'
]

expected_tables = [
    'ASSETS', 'DOCKER_SERVICES', 'ASSETS_AVAIL', 'ASSETS_TYPE'
]

client = KSQLDBClient('http://localhost:8088')
wait_for_streams_and_tables(client, expected_streams, expected_tables)
