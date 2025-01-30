import os
import asyncio
from asyncua import Client
from asyncua import ua
from asyncua.ua import uaerrors
from basesupervisor import BaseSupervisor


class OPCUASupervisor(BaseSupervisor):
    """
    OpenFactory Device Command Supervisor using OPC UA to communicate with a device command adapter
    """

    namespace_uri = os.getenv('NAMESPACE_URI', 'openfactory')
    browseName = os.getenv('BROWSE_NAME', 'ZAIX-001')

    RECONNECT_INTERVAL = 10  # Time in seconds to wait before trying to reconnect

    def __init__(self, device_uuid: str, ksql_url: str, adapter_ip: str, adapter_port: int = 4840):
        """
        Initialize the OPCUASupervisor

        :param device_uuid: The UUID of the device to listen for commands
        :param ksql_url: The URL of the ksqlDB server
        :param adapter_ip: The IP address of the adapter
        :param adapter_port: The port of the adapter
        """
        super().__init__(device_uuid, ksql_url)
        self.adapter_ip = adapter_ip
        self.adapter_port = adapter_port
        self.opcua_client = Client(f"opc.tcp://{self.adapter_ip}:{self.adapter_port}")
        self.idx = None
        self.opcua_adapter = None
        self._stop_reconnect = False

        # Connect to adapter and start monitoring
        self._event_loop.run_until_complete(self._connect_to_adapter())
        self._event_loop.create_task(self._monitor_adapter())

    async def _connect_to_adapter(self):
        """
        Attempt to connect to the adapter at the specified address
        """
        self.commands = []
        try:
            await self.opcua_client.connect()
            self.idx = await self.opcua_client.get_namespace_index(self.namespace_uri)
            objects = self.opcua_client.get_objects_node()
            self.opcua_adapter = await objects.get_child([f"{self.idx}:{self.browseName}"])
            print(f"Connected to adapter at opc.tcp://{self.adapter_ip}:{self.adapter_port}")
            self.connectionStatus = "ESTABLISHED"

            # Get methods of the OPC UA adapter
            await self._fetch_available_commands()

        except Exception as e:
            print(f"Failed to connect to adapter at {self.adapter_ip}:{self.adapter_port}: {e}")
            try:
                await self.opcua_client.disconnect()
                print("Disconnected from OPC UA server.")
            except Exception as e:
                print(f"Error during OPC UA disconnection: {e}")
            self.connectionStatus = "CLOSED"

        msg = [
            {
                "device_uuid": self.supervisor_uuid,
                "id": "adapter_uri",
                "value": f"opc.tcp://{self.adapter_ip}:{self.adapter_port}",
                "tag": 'AdapterURI',
                "type": 'Events'
            },
            {
                "device_uuid": self.supervisor_uuid,
                "id": "adapter_connection_status",
                "value": self.connectionStatus,
                "tag": 'ConnectionStatus',
                "type": 'Events'
            }
        ]
        try:
            self.ksql.insert_into_stream('DEVICES_STREAM', msg)
        except Exception as e:
            print(f"Failed to send adapter connection status message for supervisor: {e}")
        return

    async def _fetch_available_commands(self):
        """
        Fetch commands from OPC UA server
        """
        if not self.opcua_adapter:
            return
        methods = await self.opcua_adapter.get_methods()
        print(f"Exposed methods for supervisor adapter {self.browseName}:")

        for method_node in methods:
            # Fetch and print the method's browse name
            node_id = method_node.nodeid
            identifier = node_id.Identifier

            try:
                # Fetch and print the method's display name (similar to interactive example)
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

    def available_commands(self):
        return self.commands

    async def _monitor_adapter(self):
        """
        Continuously monitor the connection to the adapter and attempt reconnections if disconnected.
        """
        while not self._stop_reconnect:
            if self.connectionStatus == 'CLOSED':
                print("Attempting to reconnect to adapter...")
                await self._connect_to_adapter()
                self._send_available_commands()
            await asyncio.sleep(self.RECONNECT_INTERVAL)

    async def shutdown(self):
        """ Gracefully shut down the supervisor """
        self._stop_reconnect = True
        try:
            await self.opcua_client.disconnect()
            print("Disconnected from OPC UA server.")
        except Exception as e:
            print(f"Error during OPC UA disconnection: {e}")

        await super().shutdown()
        print("Shutdown completed")

    async def new_cmd(self, cmd, args):
        """
        Handle a new command

        :param cmd:  The command received from the ksqlDB stream
        :param args: The arguments of the command received from the ksqlDB stream
        """
        # Check if the adapter is connected before sending the command
        try:
            await self.opcua_client.check_connection()
        except Exception as e:
            print("No connection to adapter. Cannot send command.", e)
            # attempts to reconnect
            await self._connect_to_adapter()
            if self.connectionStatus == 'CLOSED':
                return

        # request execution of method on OPCUA server
        try:
            ret = await self.opcua_adapter.call_method(f"{self.idx}:{cmd.strip()}",
                                                       ua.Variant(args.strip(), ua.VariantType.String))
        except uaerrors:
            ret = "Unknown method"

        return ret


def main():

    supervisor = OPCUASupervisor(
        device_uuid=os.getenv('DEVICE_UUID', 'ZAIX-001'),
        ksql_url=os.getenv('KSQL_URL', 'http://localhost:8088'),
        adapter_ip=os.getenv('ADAPTER_IP', '127.0.0.1'),
        adapter_port=os.getenv('ADAPTER_PORT', 4840)
    )

    supervisor.run()


if __name__ == '__main__':
    main()
