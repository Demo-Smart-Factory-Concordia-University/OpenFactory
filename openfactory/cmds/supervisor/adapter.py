import socket


"""
Simple TCL Adapter that can be used as start point to develop specific adapters
It will handle commands sent from a TCPSupervisor
"""


class Adapter:
    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        """
        Initialize the Adapter.

        :param host: The IP address to listen on.
        :param port: The port to listen on.
        """
        self.host = host
        self.port = port
        self.running = True

    def start(self):
        """
        Start the adapter to listen for incoming connections and handle commands.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.host, self.port))
            server_socket.listen(1)
            print(f"Adapter listening on {self.host}:{self.port}")

            while self.running:
                client_socket, client_address = server_socket.accept()
                print(f"Connected to supervisor at {client_address}")
                self.handle_client(client_socket)

    def handle_client(self, client_socket):
        """
        Handle communication with the connected supervisor.

        :param client_socket: The socket connected to the supervisor.
        """
        with client_socket:
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    print("Supervisor disconnected.")
                    break

                print(f"Received command: {data.decode('utf-8')}")

                # Handle commands
                if data.decode('utf-8') == 'stop':
                    print("Received stop command. Shutting down...")
                    self.running = False
                    break
                if data.decode('utf-8') == 'ping':
                    print("Received ping command. ")
                    # add further logic as desired

        client_socket.close()
        print("Server socket closed.")


if __name__ == "__main__":
    adapter = Adapter(host="127.0.0.1", port=7877)
    adapter.start()
