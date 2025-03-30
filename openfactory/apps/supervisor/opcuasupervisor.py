import os
import asyncio
import threading
from asyncua import Client, ua
from openfactory.apps.supervisor import BaseSupervisor
from openfactory.assets import AssetAttribute
import openfactory.config as config


class OPCUASupervisor(BaseSupervisor):
    """
    OpenFactory Device Command Supervisor using OPC UA to communicate with the device command adapter
    """

    namespace_uri = os.getenv('NAMESPACE_URI', 'demofactory')
    browseName = os.getenv('BROWSE_NAME', 'PROVER3018')

    RECONNECT_INTERVAL = 10  # Time in seconds to wait before trying to reconnect

    def __init__(self, supervisor_uuid: str, device_uuid: str, adapter_ip: str, adapter_port: int = 4840,
                 ksqldb_url=config.KSQLDB, bootstrap_servers=config.KAFKA_BROKER):
        """
        Initialize the OPCUASupervisor

        :param supervisor_uuid: UUID of the supervisor
        :param device_uuid: UUID of the device to listen for commands
        :param adapter_ip: IP address of the adapter
        :param adapter_port: port of the adapter
        :param ksql_url: URL of the ksqlDB server
        :param bootstrap_servers: kafka broker of Kaka cluster
        """
        super().__init__(supervisor_uuid=supervisor_uuid, device_uuid=device_uuid,
                         ksqldb_url=ksqldb_url, bootstrap_servers=bootstrap_servers)

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

    def _start_event_loop(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def _run_command(self, cmd, args):
        """ Request to run command on OPCUA server """
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
            print(f"An unknown method '{cmd.strip()}' was requested")
            ret = "Unknown method"
        except ConnectionError:
            print("No connection to adapter. Cannot send command.")
            await self.opcua_client.disconnect()
            self.adapter_connection_status = "CLOSED"
            ret = "No connection to OPC UA server"
        except Exception as e:
            print(f"An unexpected error occurred while connecting to the OPCUA server: {e}")
            print(f"Error type: {type(e)}")
            ret = f"Unknown error {e}"

        return ret

    def on_command(self, msg_key, msg_value):
        """ Callback to process received commands """
        cmd = msg_value['CMD']
        args = msg_value['ARGS']

        self._event_loop.call_soon_threadsafe(
            lambda: asyncio.create_task(self._run_command(cmd, args))
        )

    def available_commands(self):
        """ Return the list of commands handled by the supervisor """
        return self.commands

    async def _fetch_available_commands(self):
        """
        Fetch commands exposed by OPC UA server
        """
        if not self.opcua_adapter:
            return
        methods = await self.opcua_adapter.get_methods()
        print(f"Exposed methods by supervisor adapter {self.browseName}:")

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
                print(f"   Method: {display_name.Text} ({description.Text})")
            except Exception as e:
                print(f"   Failed to get browse name for method {identifier}: {e}")

    async def _connect_to_adapter(self):
        """
        Attempt to connect to the adapter
        """
        self.commands = []
        try:
            await self.opcua_client.connect()
            self.idx = await self.opcua_client.get_namespace_index(self.namespace_uri)
            objects = self.opcua_client.get_objects_node()
            self.opcua_adapter = await objects.get_child([f"{self.idx}:{self.browseName}"])
            print(f"Connected to adapter at opc.tcp://{self.adapter_ip}:{self.adapter_port}")
            self._send_available_commands()
            self.adapter_connection_status = "ESTABLISHED"

            # Get methods of the OPC UA adapter
            await self._fetch_available_commands()

        except Exception as e:
            print(f"Failed to connect to adapter at {self.adapter_ip}:{self.adapter_port}: {e}")
            try:
                await self.opcua_client.disconnect()
                print("Disconnected from OPC UA server")
            except Exception as e:
                print(f"Error during OPC UA disconnection: {e}")
            self.adapter_connection_status = "CLOSED"

    async def _monitor_adapter(self):
        """
        Continuously monitor the connection to the adapter and attempt reconnections if disconnected
        """
        while not self._stop_reconnect:
            if self.adapter_connection_status.value == "CLOSED":
                print("\nAttempting to reconnect to adapter...")
                await self._connect_to_adapter()
            await asyncio.sleep(self.RECONNECT_INTERVAL)
        print("Stopped monitoring connection to OPC UA server")

    def app_event_loop_stopped(self):
        """ Gracefully shut down the supervisor """
        self._stop_reconnect = True
        try:
            asyncio.run_coroutine_threadsafe(self.opcua_client.disconnect(), self._event_loop)
            print("Disconnected from OPC UA server")
        except Exception as e:
            print(f"Error during OPC UA disconnection: {e}")

        super().app_event_loop_stopped()
        print("Shutdown completed")


if __name__ == "__main__":

    # Example usage of OPCUASupervisor class

    supervisor = OPCUASupervisor(
        supervisor_uuid='DEMO-SUPERVISOR',
        device_uuid='PROVER3018',
        adapter_ip='192.168.0.201',
        adapter_port=4840,
        ksqldb_url="http://localhost:8088",
        bootstrap_servers="localhost:9092"
    )

    supervisor.run()
