import os
import requests


class SICKProximitySensor():

    ip_address = os.getenv('SIG350_IP')
    device_alias = os.getenv('DEVICE_ALIAS')

    __available__ = 0

    def __init__(self):
        self.session = requests.Session()

    def read(self):
        """
        Read sensor value and return it as SHDR data
        """
        try:
            resp = self.session.get(f"http://{self.ip_address}/iolink/v1/devices/{self.device_alias}/processdata/value").json()
        except requests.exceptions.ConnectionError:
            self.__available__ = 0
            return '|avail|UNAVAILABLE'
        if self.__available__ == 0:
            self.__available__ = 1
            return '|avail|AVAILABLE'
        if resp['getData']['cqValue']:
            return '|trigger|1'
        else:
            return '|trigger|0'
