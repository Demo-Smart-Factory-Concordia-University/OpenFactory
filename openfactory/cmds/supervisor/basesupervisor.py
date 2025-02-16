import asyncio
import signal
from pyksql.ksql import KSQL


class BaseSupervisor:
    """
    OpenFactory Device Command Supervisor
    """

    def __init__(self, device_uuid: str, ksql_url: str):
        """
        Initialize the Supervisor.

        :param device_uuid: The UUID of the device to listen for commands.
        :param ksql_url: The URL of the ksqlDB server.
        """
        self.device_uuid = device_uuid
        self.supervisor_uuid = device_uuid + "-SUPERVISOR"
        self.ksql_url = ksql_url
        self.ksql = KSQL(ksql_url)

        self.shutdown_triggered = False

        # store event loop
        self._event_loop = asyncio.get_event_loop()

    def create_ksqldb_table(self):
        """
        Create ksqlDB table and stream related to the supervisor
        Can be called by chidren if desired
        """
        # supervisor table
        supervisor_table = self.supervisor_uuid.replace('-', '_')
        self.ksql._statement_query(f"""CREATE TABLE IF NOT EXISTS {supervisor_table} AS
                                         SELECT id,
                                                LATEST_BY_OFFSET(value) AS value,
                                                LATEST_BY_OFFSET(type) AS type,
                                                LATEST_BY_OFFSET(tag) AS tag
                                         FROM devices_stream
                                         WHERE device_uuid = '{self.supervisor_uuid}'
                                         GROUP BY id;""")
        # wait table is created
        found_flag = False
        while not found_flag:
            tables = self.ksql.tables()
            for tab in tables:
                if tab.name.upper() == supervisor_table.upper():
                    found_flag = True

        # commands stream
        self.ksql._statement_query(f"""CREATE STREAM {self.device_uuid.replace('-', '_')}_cmds_stream AS
                                         SELECT *
                                         FROM cmds_stream
                                         WHERE device_uuid = '{self.device_uuid}';""")
        # commands table
        self.ksql._statement_query(f"""CREATE TABLE IF NOT EXISTS {self.device_uuid.replace('-', '_')}_CMDS AS
                                         SELECT device_uuid,
                                                LATEST_BY_OFFSET(cmd) AS cmd,
                                                LATEST_BY_OFFSET(args) AS args
                                         FROM {self.device_uuid.replace('-', '_')}_cmds_stream
                                         GROUP BY device_uuid;""")

    def send_availability(self, availability):
        """ Send Supervisor Availability message to ksqlDB """
        msg = [
            {
                "device_uuid": self.supervisor_uuid,
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

    def available_commands(self):
        """ Return the list of exposed commands by the supervisor """
        raise NotImplementedError("You must implement the 'available_commands' method.")

    def _send_available_commands(self):
        """ Send available commands to ksqlDB """
        for cmd in self.available_commands():
            msg = [
                {
                    "device_uuid": self.device_uuid,
                    "id": cmd['command'],
                    "value": cmd['description'],
                    "tag": 'Method',
                    "type": 'Method'
                }
            ]
            try:
                resp = self.ksql.insert_into_stream('DEVICES_STREAM', msg)
                print(f"Sent method {cmd['command']} | {cmd['description']}, Response: {resp}")
            except Exception as e:
                print(f"Failed to send method description: {e}")

    async def fetch_streaming_cmds(self):
        """ Fetch streaming commands from the ksqlDB stream """
        try:
            await self.ksql.query(
                query=f"SELECT CMD, ARGS FROM cmds_stream WHERE DEVICE_UUID = '{self.device_uuid.upper()}' EMIT CHANGES;",
                earliest=False,
                on_new_row=lambda row: asyncio.create_task(self.new_cmd(row[0], row[1]))
            )
        except asyncio.CancelledError:
            # Handle cancellation due to shutdown signal
            print('Supervisor was shutdown')
            return
        except Exception as e:
            print(f"An error occurred: {e}")
        print(f"ERROR - ksqlDB query for stream {self.device_uuid.replace('-', '_')}_cmds_stream terminated.\nDoes this stream exist (supervisor up?)?")

    async def new_cmd(self, cmd, args):
        """
        Handle a new command

        :param cmd:  The command received from the ksqlDB stream
        :param args: The arguments of the command received from the ksqlDB stream
        """
        raise NotImplementedError("You must implement the 'new_cmd' method.")

    async def shutdown(self):
        """ Gracefully shut down the supervisor """
        self.send_availability('UNAVAILABLE')
        msg = [
            {
                "device_uuid": self.supervisor_uuid,
                "id": "adapter_connection_status",
                "value": "CLOSED",
                "tag": 'ConnectionStatus',
                "type": 'Events'
            }
        ]
        try:
            self.ksql.insert_into_stream('DEVICES_STREAM', msg)
        except Exception as e:
            print(f"Failed to send adapter connection status message for supervisor: {e}")

    async def _main_loop(self):
        """ Main event loop for fetching commands """
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
            await self.fetch_streaming_cmds()
        except asyncio.CancelledError:
            print("Main task cancelled.")
        finally:
            await shutdown_main_loop()

    def run(self):
        """ Start the Supervisor's asyncio loop to fetch commands """
        print("-------------------------------------------------------")
        print(f"Starting OpenFactory supervisor for {self.device_uuid}")
        print("-------------------------------------------------------")
        self.send_availability('AVAILABLE')
        self._send_available_commands()
        self._event_loop.run_until_complete(self._main_loop())


class MyDeviceSupervisor(BaseSupervisor):
    async def new_cmd(self, cmd, args):
        print(f"Handling command for {self.device_uuid}: {cmd} {args}")
        # Children have to define custom logic here, e.g., forwarding the command


if __name__ == "__main__":
    supervisor = MyDeviceSupervisor(
        device_uuid="ZAIX-001",
        ksql_url="http://localhost:8088"
    )
    supervisor.run()
