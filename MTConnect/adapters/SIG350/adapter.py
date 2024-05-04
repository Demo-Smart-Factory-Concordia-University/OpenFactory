import socket
import socketserver
import getpass


class ImproperlyConfigured(Exception):
    """ Something is improperly configured """
    pass


class DeviceHandler(socketserver.BaseRequestHandler):
    """
    Reads SHDR data from a sensor
    """

    sensor = None
    data_old = ''

    def __init__(self, request, client_address, server):
        """ Constructor """
        # Configuration validations
        if self.sensor is None:
            raise ImproperlyConfigured("SICKDeviceHandler requires the attribute 'sensor' to be defined")

        socketserver.BaseRequestHandler.__init__(self, request, client_address, server)

    def handle(self):
        """ Handles connection from MTConnect Agent """
        print("Connection from {}".format(self.client_address[0]))
        self.request.sendall(("|avail|AVAILABLE\n").encode())

        # sends logged user to agent
        self.request.sendall(("|operator|" + getpass.getuser() + "\n").encode())
        self.request.settimeout(0.01)

        while 1:
            try:
                data = self.request.recv(1024)
            except socket.timeout:
                # read data here
                shdr_data = self.sensor.read()
                if shdr_data != self.data_old:
                    self.request.sendall((shdr_data + "\n").encode())
                    if 'avail' not in shdr_data:
                        self.data_old = shdr_data
                continue

            if not data:
                print("Connection from Agent closed")
                break

            if data == "* PING\r\n".encode():
                self.request.sendall("* PONG 60000\n".encode())


class MTCAdapterRelay(socketserver.TCPServer):
    """
    Implements a MTConnect Adapter server
    Reads SHDR data from deviceHandler_class
    """

    adapter_port = 7878
    deviceHandler_class = None

    def __init__(self):
        """ Constructor """
        # Configuration validations
        if self.deviceHandler_class is None:
            raise ImproperlyConfigured("MTCAdapterRelay requires the attribute 'deviceHandler_class' to be defined")

        socketserver.TCPServer.__init__(self, ('', self.adapter_port), self.deviceHandler_class)
