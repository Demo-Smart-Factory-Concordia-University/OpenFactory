import socket


class Adapter:
    """
    Simple (and not complete) adapter
    Sends |avail|AVAILABLE to agetn on connection
    """
    def __init__(self, host='0.0.0.0', port=7800):
        self.host = host
        self.port = port
        self.server_socket = None

    def start(self):
        """ Start listening for incoming connections """
        # Create a socket object
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the socket to the address (host, port)
        self.server_socket.bind((self.host, self.port))

        # Start listening for incoming connections (max 5 connections in the backlog)
        self.server_socket.listen(5)
        print(f"Adapter listening on {self.host}:{self.port}")

        try:
            while True:
                # Accept a new connection
                client_socket, client_address = self.server_socket.accept()
                print(f"Connection from {client_address}")

                # Receive data from the client (up to 1024 bytes)
                data = client_socket.recv(1024)

                if data:
                    print(f"Received data: {data.decode('utf-8')}")

                # Send a response message to the client
                self.send(client_socket, "|avail|AVAILABLE\n")

        except KeyboardInterrupt:
            print("\nAdapter interrupted. Shutting down...")
        finally:
            self.stop()

    def send(self, client_socket, message):
        """ Send a message to the client """
        client_socket.sendall(message.encode('utf-8'))
        print(f"Sent message: {message}")

    def stop(self):
        """ Stop the adapter and close the socket """
        if self.server_socket:
            self.server_socket.close()
            print("Adapter stopped")


if __name__ == "__main__":
    adapter = Adapter(port=7800)
    adapter.start()
