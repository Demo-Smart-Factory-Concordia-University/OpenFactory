import asyncio
import signal
import time
from pyksql.ksql import KSQL


class SinkConnector:
    """
    OpenFactory Generic Sink Connector
    """

    def __init__(self, connector_uuid: str, service_stream: str, ksql_url: str):
        """
        Initialize the Sink Connector

        :param connector_uuid: UUDI of the sink connector
        :param service_stream: ksqlDB stream for which this connector operates
        :param ksql_url: URL of the ksqlDB server
        """
        self.service_stream = service_stream
        self.connector_uuid = connector_uuid
        self.ksql_url = ksql_url
        self.ksql = KSQL(ksql_url)
        self.create_ksqldb_table()
        self.shutdown_triggered = False

        # store event loop
        self._event_loop = asyncio.get_event_loop()

    def create_ksqldb_table(self):
        """ Create ksqlDB table related to the supervisor """
        # sink connector table
        connector_table = self.connector_uuid.replace('-', '_')
        resp = self.ksql._statement_query(f"""CREATE TABLE IF NOT EXISTS {connector_table} AS
                                              SELECT id,
                                                    LATEST_BY_OFFSET(value) AS value,
                                                    LATEST_BY_OFFSET(type) AS type,
                                                    LATEST_BY_OFFSET(tag) AS tag
                                              FROM devices_stream
                                              WHERE device_uuid = '{self.connector_uuid}'
                                              GROUP BY id;""")
        if resp.status_code != 200:
            print(f"Failed to create table '{connector_table}': {resp.text}")
        print(f"Created ksqlDB table {connector_table}")

        # wait table is created
        for _ in range(5):
            time.sleep(1)
            tables = self.ksql.tables()
            if any(table.name.upper() == connector_table.upper() for table in tables):
                return

    def send_availability(self, availability):
        """ Send Connector Availability message to ksqlDB """
        msg = [
            {
                "device_uuid": self.connector_uuid,
                "id": "avail",
                "value": availability,
                "tag": 'Availability',
                "type": 'Events'
            }
        ]
        try:
            resp = self.ksql.insert_into_stream('DEVICES_STREAM', msg)
            print(f"Sent availability message: {availability}, Response: {resp}")
        except Exception as e:
            print(f"Failed to send availability message: {e}")

    def send_inital_msg(self, inital_msg=[]):
        """ Send inital message to ksqlDB """
        msg = [
            {
                "device_uuid": self.connector_uuid,
                "id": "service_uuid",
                "value": self.service_stream,
                "tag": 'StreamUuid',
                "type": 'Events'
            }
        ]
        try:
            resp = self.ksql.insert_into_stream('DEVICES_STREAM', msg + inital_msg)
            print(f"Sent inital message, Response: {resp}")
        except Exception as e:
            print(f"Failed to send inital message: {e}")

    def stream_query(self):
        """ Return query for service stream. Can be redefined by children """
        return f"SELECT * FROM {self.service_stream} EMIT CHANGES;"

    async def fetch_streaming_data(self):
        """ Fetch streaming data from the ksqlDB stream of the dOpenFactory device """
        try:
            await self.ksql.query(
                query=self.stream_query(),
                earliest=False,
                on_new_row=lambda row: asyncio.create_task(self.new_data(row))
            )
        except asyncio.CancelledError:
            # Handle cancellation due to shutdown signal
            print('Sink connector is shutdown')
            return
        except Exception as e:
            print(f"An error occurred: {e}")
        print(f"ERROR - ksqlDB query for stream {self.service_stream} terminated.\nDoes this stream exist ?")

    async def new_data(self, data):
        """
        Handle a new data

        :param data:  The data received from the ksqlDB device stream
        """
        raise NotImplementedError("You must implement the 'new_data' method.")

    async def shutdown(self):
        """ Gracefully shut down the supervisor """
        self.send_availability('UNAVAILABLE')

    async def _main_loop(self):
        """ Main event loop for fetching data """
        async def shutdown_main_loop():
            if not self.shutdown_triggered:
                print("Shutting down...")
                self.shutdown_triggered = True
                await self.shutdown()
                # Cancel all running tasks
                tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

        # Register signal handlers within the running loop
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown_main_loop()))

        try:
            await self.fetch_streaming_data()
        except asyncio.CancelledError:
            print("Main task cancelled.")
        finally:
            await shutdown_main_loop()

    def run(self):
        """ Start the Sink Connector's asyncio loop to fetch device data """
        print("--------------------------------------------------------------")
        print(f"Starting OpenFactory sink connector for {self.service_stream}")
        print("--------------------------------------------------------------")
        self.send_availability('AVAILABLE')
        self.send_inital_msg()
        print("Starting main loop")
        self._event_loop.run_until_complete(self._main_loop())


class MySinkConnector(SinkConnector):
    """
    Example usage
    """
    async def new_data(self, data):
        # For actual use case, add here your logic to process the fetched data
        print(f"Handling data from {self.device_uuid}: {data}")

    def send_inital_msg(self, inital_msg=[]):
        """ Sends additonal inital message at start """
        msg = [
            {
                "device_uuid": self.connector_uuid,
                "id": "version",
                "value": "1.0",
                "tag": "Version",
                "type": 'Events'
            }
        ]
        super().send_inital_msg(msg)


if __name__ == "__main__":
    connector = MySinkConnector(
        connector_uuid='ZAIX-001-CONNECTOR',
        service_stream="ZAIX_001_STREAM",
        ksql_url="http://localhost:8088"
    )
    connector.run()
