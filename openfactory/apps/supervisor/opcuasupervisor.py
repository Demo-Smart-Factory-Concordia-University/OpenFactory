""" OpenFactory Supervisor using OPC UA to communicate. """

import os
import asyncio
import threading
from asyncua import Client, ua
from openfactory.kafka.ksql import KSQLDBClient
from openfactory.apps.supervisor import BaseSupervisor
from openfactory.assets import AssetAttribute
import openfactory.config as config


class OPCUASupervisor(BaseSupervisor):
    """
    OpenFactory Supervisor using OPC UA to communicate with the device command adapter.

    This supervisor extends the `BaseSupervisor` class and provides functionality to interact with an OPC UA
    adapter. It connects to the device command adapter via OPC UA, monitors the connection, and processes incoming
    commands for the associated device.

    Attributes:
        namespace_uri (str): The namespace URI for the OPC UA server.
        browseName (str): The browse name used to access the device in the OPC UA server.
        RECONNECT_INTERVAL (int): The interval (in seconds) to wait before attempting to reconnect to the adapter in case of a failure.

        adapter_ip (str): Instance attribute - The IP address of the OPC UA adapter.
        adapter_port (int): Instance attribute - The port of the OPC UA adapter.
        opcua_client (asyncua.Client): Instance attribute - The OPC UA client instance used for connecting to the adapter.
        idx (int or None): Instance attribute - The index of the namespace in the OPC UA server.
        opcua_adapter (str): Instance attribute - A reference to the OPC UA adapter (for internal use).
        _stop_reconnect (bool): Instance attribute - A flag to stop reconnecting to the adapter once the supervisor is stopped.
        _event_loop (asyncio.EventLoop): Instance attribute - The event loop used to run asynchronous operations related to the adapter connection.

    Example usage:
        .. code-block:: python

            from openfactory.apps.supervisor import OPCUASupervisor
            from openfactory.kafka import KSQLDBClient

            supervisor = OPCUASupervisor(
                supervisor_uuid='DEMO-SUPERVISOR',
                device_uuid='PROVER3018',
                adapter_ip='192.168.0.201',
                adapter_port=4840,
                ksqlClient=KSQLDBClient("http://localhost:8088"),
                bootstrap_servers='localhost:9092'
            )

            supervisor.run()
    """

    namespace_uri = os.getenv('NAMESPACE_URI', 'demofactory')
    browseName = os.getenv('BROWSE_NAME', 'PROVER3018')

    RECONNECT_INTERVAL = 10  # Time in seconds to wait before trying to reconnect

    def __init__(self, supervisor_uuid: str, device_uuid: str, adapter_ip: str, adapter_port: int,
                 ksqlClient: KSQLDBClient, bootstrap_servers: str = config.KAFKA_BROKER,
                 loglevel: str = 'INFO'):
        """
        Initialize the OPCUASupervisor.

        Initializes the supervisor by setting up the OPC UA client and connecting to the OPC UA
        adapter using the provided IP address and port. It also initializes necessary attributes, including
        the connection URI, connection status, and other OPC UA-related settings.

        Args:
            supervisor_uuid (str): UUID of the supervisor.
            device_uuid (str): UUID of the device to listen for commands.
            adapter_ip (str): The IP address of the OPC UA adapter.
            adapter_port (int): The port on which the OPC UA adapter is accessible.
            ksqlClient (KSQLDBClient): The KSQL client instance used for querying.
            bootstrap_servers (str): Kafka bootstrap server URL.
            loglevel (str): Logging level for the supervisor (e.g., 'INFO', 'DEBUG'). Defaults to 'INFO'.
        """
        super().__init__(supervisor_uuid=supervisor_uuid, device_uuid=device_uuid,
                         ksqlClient=ksqlClient, bootstrap_servers=bootstrap_servers,
                         loglevel=loglevel)

        self.adapter_ip = adapter_ip
        self.adapter_port = adapter_port
        self.opcua_client = Client(f"opc.tcp://{self.adapter_ip}:{self.adapter_port}")
        self.idx = None
        self.opcua_adapter = None
        self._stop_reconnect = False

        # attributes of supervisor
        self.add_attribute(
            attribute_id='adapter_uri',
            asset_attribute=AssetAttribute(
                value=f"opc.tcp://{self.adapter_ip}:{self.adapter_port}",
                type='Events',
                tag='AdapterURI'
            )
        )
        self.add_attribute(
            attribute_id='adapter_connection_status',
            asset_attribute=AssetAttribute(
                value='UNAVAILABLE',
                type='Events',
                tag='ConnectionStatus'
            )
        )
        self.add_attribute(
            attribute_id='opcua_namespace_uri',
            asset_attribute=AssetAttribute(
                value=self.namespace_uri,
                type='Events',
                tag='OPCUANamespaceURI'
            )
        )
        self.add_attribute(
            attribute_id='opcua_browseName',
            asset_attribute=AssetAttribute(
                value=self.browseName,
                type='Events',
                tag='OPCUABrowsName'
            )
        )

        # Create a dedicated event loop and run it in a separate thread
        self._event_loop = asyncio.new_event_loop()
        threading.Thread(target=self._start_event_loop, args=(self._event_loop,), daemon=True).start()

        # Connect to adapter and start monitoring connection
        asyncio.run_coroutine_threadsafe(self._connect_to_adapter(), self._event_loop)
        asyncio.run_coroutine_threadsafe(self._monitor_adapter(), self._event_loop)

    def welcome_banner(self) -> None:
        """ Welcome banner. """
        print("--------------------------------------------------")
        print("OpenFactory OPC-UA Device Supervisor")
        print("(c) Rolf Wuthrich, Concordia Univerity")
        print("--------------------------------------------------")
        print(f"SUPERVISOR_UUID: {self.asset_uuid}")
        print(f"DEVICE_UUID:     {self._device_uuid}")
        print(f"NAMESPACE_URI:   {self.namespace_uri}")
        print(f"BROWSE_NAME:     {self.browseName}")
        print(f"ADAPTER_IP:      {self.adapter_ip}")
        print(f"ADAPTER_PORT:    {self.adapter_port}")
        print(f"KSQL_HOST:       {self.ksql.ksqldb_url}")
        print(f"KAFKA_BROKER:    {self.bootstrap_servers}")
        print("--------------------------------------------------")

    def _start_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        Starts the event loop for running asynchronous tasks.

        Responsible for setting the provided asyncio event loop as the current event loop
        and then running it indefinitely using `loop.run_forever()`. It is typically called in a separate
        thread to handle asynchronous operations such as connecting to and monitoring the OPC UA client.

        Args:
            loop (asyncio.AbstractEventLoop): The asyncio event loop instance that will be run indefinitely in the background.

        Notes:
            - This method is important because OPC UA communication (e.g., `opcua_client`) involves asynchronous
              operations that need an event loop to manage them.
            - Running the event loop in a separate thread allows the main application to remain responsive while
              the OPC UA client operates asynchronously in the background.
        """
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def _run_command(self, cmd: str, args: str) -> str:
        """
        Requests to run a command on the OPC UA server.

        Attempts to check the connection to the OPC UA client and reconnect if necessary.
        It then sends the provided command to the OPC UA adapter, passing any arguments in the form of
        a string. The method handles different error scenarios, including connection issues and method
        not being found on the server, and returns the outcome or error message.

        Args:
            cmd (str): The name of the command to execute on the OPC UA server.
            args (str): The arguments to pass to the command, as a space-separated string.

        Returns:
            str: The result of the method call, or an error message if the command could not be executed.

        Exceptions:
            - If the connection to the OPC UA client fails, it attempts to reconnect using `_connect_to_adapter()`.
            - If the requested command does not exist on the OPC UA server, a message indicating the method is unknown is returned.
            - If the connection to the OPC UA server is lost during the command execution, the connection is reset and an error message is returned.
            - Any other unforeseen errors are caught and logged, with the error message being returned.
        """
        try:
            await self.opcua_client.check_connection()
        except Exception:
            await self._connect_to_adapter()

        try:
            ret = await self.opcua_adapter.call_method(
                f"{self.idx}:{cmd.strip()}",
                ua.Variant(args.strip(), ua.VariantType.String)
            )
        except ua.uaerrors._auto.BadNoMatch:
            self.logger.warning(f"An unknown method '{cmd.strip()}' was requested")
            ret = "Unknown method"
        except ConnectionError:
            self.logger.warning("No connection to adapter. Cannot send command.")
            await self.opcua_client.disconnect()
            self.adapter_connection_status = "CLOSED"
            ret = "No connection to OPC UA server"
        except Exception as e:
            self.logger.exception("An unexpected error occurred while connecting to the OPCUA server.")
            ret = f"Unknown error {e}"

        return ret

    def on_command(self, msg_key: str, msg_value: dict) -> None:
        """
        Callback method to process received commands.

        Is invoked when a command message is received for the device associated with this supervisor.
        It extracts the command and its arguments from the message and schedules the execution of the corresponding
        command on the OPC UA server in the event loop.

        Args:
            msg_key (str): The key of the Kafka message, typically identifying the source of the command.
            msg_value (dict): Dictionary with required keys 'CMD' (command string) and 'ARGS' (space-separated args).

        Example:
            .. code-block:: python

                self.on_command(
                    "DEVICE-456",
                    {"CMD": "start", "ARGS": "--verbose --timeout 5"}
                )
        """
        cmd = msg_value['CMD']
        args = msg_value['ARGS']

        self._event_loop.call_soon_threadsafe(
            lambda: asyncio.create_task(self._run_command(cmd, args))
        )

    def available_commands(self) -> list[str]:
        """
        Return the list of commands handled by the supervisor.

        Returns:
            list: A list of dictionaries, each containing 'command' (str) and 'description' (str).
        """
        return self.commands

    async def _fetch_available_commands(self) -> None:
        """
        Fetch commands exposed by the OPC UA server and update the list of available commands.

        Queries the connected OPC UA server for the methods (commands) that are
        exposed by the device, and appends them to the list of available commands. Each
        method exposed by the OPC UA server is represented as a command with a description
        that can be executed by the supervisor.

        It fetches the following information for each exposed method:
            - The command name (display name) from the OPC UA server.
            - The description of the command (if available).

        The commands are added to the `self.commands` list in the format:
            {
                "command": <command_name>,
                "description": <command_description>
            }

        Raises:
            Exception: If there is an error while fetching the methods from the OPC UA server.
        """
        if not self.opcua_adapter:
            return
        methods = await self.opcua_adapter.get_methods()
        self.logger.info(f"Exposed methods by supervisor adapter {self.browseName}:")

        for method_node in methods:
            node_id = method_node.nodeid
            identifier = node_id.Identifier
            try:
                display_name = await method_node.read_display_name()
                description = await method_node.read_description()
                command_dict = {
                    "command": display_name.Text,
                    "description": description.Text
                }
                self.commands.append(command_dict)
                self.logger.info(f"   Method: {display_name.Text} ({description.Text})")
            except Exception:
                self.logger.exception(f"   Failed to get browse name for method {identifier}.")

    async def _connect_to_adapter(self) -> None:
        """
        Attempt to connect to the OPC UA adapter and set up the connection.

        Establishes a connection to the OPC UA server using the provided adapter IP and port.
        Once connected, it fetches the namespace index, retrieves the adapter object, and attempts to fetch
        the available methods (commands) from the OPC UA adapter.

        If the connection is successful:
            - The connection status is updated to "ESTABLISHED".
            - Available commands from the OPC UA adapter are fetched and sent to the device.

        If the connection fails, the method handles the error by:
            - Printing an error message.
            - Attempting to disconnect from the server if a connection was established.
            - Updating the connection status to "CLOSED".

        Raises:
            Exception: If any error occurs during the connection process, an exception is raised and handled.
        """
        self.commands = []
        try:
            await self.opcua_client.connect()
            self.idx = await self.opcua_client.get_namespace_index(self.namespace_uri)
            objects = self.opcua_client.get_objects_node()
            self.opcua_adapter = await objects.get_child([f"{self.idx}:{self.browseName}"])
            self.logger.info(f"Connected to adapter at opc.tcp://{self.adapter_ip}:{self.adapter_port}")

            # Get methods of the OPC UA adapter
            await self._fetch_available_commands()
            self._send_available_commands()
            self.adapter_connection_status = "ESTABLISHED"

        except Exception as e:
            self.logger.error(f"Failed to connect to adapter at {self.adapter_ip}:{self.adapter_port}: {e}")
            try:
                await self.opcua_client.disconnect()
                self.logger.error("Disconnected from OPC UA server")
            except Exception:
                self.logger.exception("Error during OPC UA disconnection.")
            self.adapter_connection_status = "CLOSED"

    async def _monitor_adapter(self) -> None:
        """
        Continuously monitor the connection to the OPC UA adapter and attempt reconnections if disconnected.

        Runs in an infinite loop (until `_stop_reconnect` is set to `True`) to monitor the connection status to the OPC UA adapter.
        If the connection is detected as "CLOSED", the method will attempt to reconnect to the adapter by calling `_connect_to_adapter()`.
        It checks the connection status every `RECONNECT_INTERVAL` seconds.
        """
        while not self._stop_reconnect:
            if self.adapter_connection_status.value == "CLOSED":
                self.logger.info("\nAttempting to reconnect to adapter...")
                await self._connect_to_adapter()
            await asyncio.sleep(self.RECONNECT_INTERVAL)
        self.logger.info("Stopped monitoring connection to OPC UA server")

    def app_event_loop_stopped(self) -> None:
        """
        Gracefully shut down the supervisor and its associated connections.

        Responsible for stopping the event loop, gracefully disconnecting
        from the OPC UA server, and performing any necessary cleanup when the application
        is shutting down. It also sets the `_stop_reconnect` flag to `True` to stop the
        connection monitoring loop.

        Raises:
            Exception: If any error occurs during the disconnection from the OPC UA server, it is caught and logged.
        """
        self._stop_reconnect = True
        try:
            asyncio.run_coroutine_threadsafe(self.opcua_client.disconnect(), self._event_loop)
            self.logger.info("Disconnected from OPC UA server")
        except Exception:
            self.logger.exception("Error during OPC UA disconnection.")

        super().app_event_loop_stopped()
        self.logger.info("Shutdown completed")


if __name__ == "__main__":

    # Example usage of the OPCUASupervisor
    from openfactory.kafka import KSQLDBClient

    supervisor = OPCUASupervisor(
        supervisor_uuid=os.getenv('SUPERVISOR_UUID', 'DEMO-SUPERVISOR'),
        device_uuid=os.getenv('DEVICE_UUID', 'PROVER3018'),
        adapter_ip=os.getenv('ADAPTER_IP', '192.168.0.201'),
        adapter_port=os.getenv('ADAPTER_PORT', 4840),
        ksqlClient=KSQLDBClient("http://localhost:8088"),
        bootstrap_servers=os.getenv('KAFKA_BROKER', 'localhost:9092')
    )

    supervisor.run()
