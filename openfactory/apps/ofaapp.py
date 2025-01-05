import asyncio
import signal
import time
from pyksql.ksql import KSQL


class OpenFactoryApp:
    """
    Generic OpenFactory App
    """

    def __init__(self, app_uuid: str, ksql_url: str):
        """
        Initialize the OpenFactory App

        :param app_uuid: UUDI of the app
        :param ksql_url: URL of the ksqlDB server
        """
        self.app_uuid = app_uuid
        self.ksql_url = ksql_url
        self.ksql = KSQL(ksql_url)
        self._create_ksqldb_table()
        self.shutdown_triggered = False

    def _create_ksqldb_table(self):
        """ Create ksqlDB table related to the app """
        # app table
        app_table = self.app_uuid.replace('-', '_')
        resp = self.ksql._statement_query(f"""CREATE TABLE IF NOT EXISTS {app_table} AS
                                              SELECT id,
                                                    LATEST_BY_OFFSET(value) AS value,
                                                    LATEST_BY_OFFSET(type) AS type,
                                                    LATEST_BY_OFFSET(tag) AS tag
                                              FROM devices_stream
                                              WHERE device_uuid = '{self.app_uuid}'
                                              GROUP BY id;""")
        if resp.status_code != 200:
            print(f"Failed to create table '{app_table}': {resp.text}")
        print(f"Created ksqlDB table {app_table}")

        # wait table is created
        for _ in range(5):
            time.sleep(1)
            tables = self.ksql.tables()
            if any(table.name.upper() == app_table.upper() for table in tables):
                return

    def send_availability(self, availability):
        """ Send App Availability message to ksqlDB """
        msg = [
            {
                "device_uuid": self.app_uuid,
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

    def welcome_banner(self):
        """
        Welcome banner printed to stdout
        Can be redefined by children
        """
        print("--------------------------------------------------------------")
        print(f"Starting OpenFactory App {self.app_uuid}")
        print("--------------------------------------------------------------")

    def initial_message(self):
        """
        Intial message to be sent to ksqlDB when App is started
        Can be defined by children
        """
        return []

    def _send_inital_msg(self):
        """ Send inital message to ksqlDB """
        msg = self.initial_message()
        if msg == []:
            return
        try:
            resp = self.ksql.insert_into_stream('DEVICES_STREAM', msg)
            print(f"Sent inital message, Response: {resp}")
        except Exception as e:
            print(f"Failed to send inital message: {e}")

    async def _app_event_loop(self):
        """
        Event loop of OpenFactory App
        Regiters SIGINT and SIGTERM signal for gracefull shutdown
        Calls main_loop()
        """
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
            await self.main_loop()
        except asyncio.CancelledError:
            print("Main task cancelled")
        finally:
            await shutdown_main_loop()

    async def main_loop(self):
        """"
        Main loop of OpenFactory App
        Must be implemented by children
        Blocking calls (e.g. time.sleep) will not allow for proper signal capture
        """
        raise NotImplementedError("Method 'event_loop' must be implemented")

    async def shutdown(self):
        """ Gracefully shut down the app """
        self.send_availability('UNAVAILABLE')

    def run(self):
        """ Run the OpenFactory app """
        self.welcome_banner()
        self.send_availability('AVAILABLE')
        self._send_inital_msg()
        print("Starting main loop")
        asyncio.run(self._app_event_loop())


class MyApp(OpenFactoryApp):
    """
    Example usage
    """

    async def main_loop(self):
        # For actual use case, add here your logic of the app
        print("I am the main loop of the app.\nI don't do anything usefull in this example.")
        counter = 1
        while True:
            print(counter)
            counter += 1
            await asyncio.sleep(2)

    def initial_message(self):
        """ Inital message of App """
        msg = [
            {
                "device_uuid": self.app_uuid,
                "id": "version",
                "value": "1.0",
                "tag": "Version",
                "type": 'Events'
            }
        ]
        return msg


if __name__ == "__main__":
    app = MyApp(
        app_uuid='DEMO-APP',
        ksql_url="http://localhost:8088"
    )
    app.run()
