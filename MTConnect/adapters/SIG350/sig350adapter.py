import sys
from adapter import MTCAdapterRelay, DeviceHandler
from sig350 import SICKProximitySensor


class ProxySensor(DeviceHandler):
    """
    SICK Proximity Sensor
    """
    sensor = SICKProximitySensor()


class SIG350Adapter(MTCAdapterRelay):
    """
    SIG350 Adapter
    """
    adapter_port = 7878
    deviceHandler_class = ProxySensor


sig350Adapter = SIG350Adapter()
try:
    sig350Adapter.serve_forever()
except KeyboardInterrupt:
    sys.exit(0)
