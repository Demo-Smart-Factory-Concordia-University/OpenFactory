import socket
import threading
import time
from basesupervisor import BaseSupervisor


class TCPSupervisor(BaseSupervisor):
    """
    OpenFactory Device Command Supervisor using TCP/IP to communicate with a device command adapter
    """

    RECONNECT_INTERVAL = 10  # Time in seconds to wait before trying to reconnect

    def __init__(self, device_uuid: str, ksql_url: str, adapter_ip: str, adapter_port: int):
        """
        Initialize the TCPSupervisor

        :param device_uuid: The UUID of the device to listen for commands
        :param ksql_url: The URL of the ksqlDB server
        :param adapter_ip: The IP address of the adapter
        :param adapter_port: The port of the adapter
        """
        super().__init__(device_uuid, ksql_url)
        self.adapter_ip = adapter_ip
        self.adapter_port = adapter_port
        self.adapter_socket = None
        self._stop_reconnect = False
        self._reconnect_thread = threading.Thread(target=self._monitor_adapter, daemon=True)
        self._reconnect_thread.start()

    def _connect_to_adapter(self):
        """
        Attempt to connect to the adapter at the specified address.
        """
        try:
            self.adapter_socket = socket.create_connection((self.adapter_ip, self.adapter_port))
            print(f"Connected to adapter at {self.adapter_ip}:{self.adapter_port}")
        except Exception as e:
            print(f"Failed to connect to adapter at {self.adapter_ip}:{self.adapter_port}: {e}")
            self.adapter_socket = None
            return

        msg = [
            {
                "device_uuid": self.supervisor_uuid,
                "id": "adapter_uri",
                "value": f"shdr://{self.adapter_ip}:{self.adapter_port}",
                "tag": 'AdapterURI',
                "type": 'Events'
            },
            {
                "device_uuid": self.supervisor_uuid,
                "id": "adapter_connection_status",
                "value": "ESTABLISHED",
                "tag": 'ConnectionStatus',
                "type": 'Events'
            }
        ]
        try:
            self.ksql.insert_into_stream('DEVICES_STREAM', msg)
        except Exception as e:
            print(f"Failed to send adapter connection status message for supervisor: {e}")

    def _monitor_adapter(self):
        """
        Continuously monitor the connection to the adapter and attempt reconnections if disconnected.
        """
        while not self._stop_reconnect:
            if not self.adapter_socket:  # No connection
                print("Attempting to reconnect to adapter...")
                self._connect_to_adapter()
            time.sleep(self.RECONNECT_INTERVAL)

    async def shutdown(self):
        """ Gracefully shut down the supervisor """
        await super().shutdown()
        self.stop()
        return
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

    def stop(self):
        """
        Stop the supervisor and its reconnection attempts.
        """
        self._stop_reconnect = True
        if self.adapter_socket:
            self.adapter_socket.close()
        print("TCPSupervisor stopped.")

    async def new_cmd(self, cmd, args):
        """
        Handle a new command

        :param cmd:  The command received from the ksqlDB stream
        :param args: The arguments of the command received from the ksqlDB stream
        """

        if len(cmd) < 1:
            print(f"Invalid command format: {cmd}")
            return

        # Format the command as "cmd args"
        cmd_str = f"{cmd} {args}"
        cmd_str = cmd_str.strip()

        # Check if the adapter is connected before sending the command
        if not self.is_adapter_connected():
            print("No connection to adapter. Cannot send command.")
            self.adapter_socket = None
            # attempts to reconnect
            self._connect_to_adapter()
            if self.adapter_socket is None:
                return

        # Send the command to the adapter
        try:
            self.adapter_socket.sendall(cmd_str.encode("utf-8"))
            print(f"Command sent to adapter: {cmd_str}")
        except (socket.error, BrokenPipeError) as e:
            print(f"Error sending command to adapter: {e}")
            self.adapter_socket = None

    def is_adapter_connected(self):
        """
        Check if the adapter is still connected using non-blocking socket
        """
        if not self.adapter_socket:
            return False

        try:
            # Set the socket to non-blocking mode
            self.adapter_socket.setblocking(False)

            # Peek into the socket to check for data
            data = self.adapter_socket.recv(1, socket.MSG_PEEK)

            # If the data is an empty byte string, the socket is not connected
            return False if data == b'' else True

        except BlockingIOError:
            # If the operation will block, set the socket back to blocking mode
            self.adapter_socket.setblocking(True)
            return True
        except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
            # Handle specific connection-related errors
            return False
        finally:
            # Always set the socket back to blocking mode before returning
            self.adapter_socket.setblocking(True)


if __name__ == "__main__":
    supervisor = TCPSupervisor(
        device_uuid="ZAIX-001",
        ksql_url="http://localhost:8088",
        adapter_ip="127.0.0.1",
        adapter_port=7877
    )
    supervisor.run()
