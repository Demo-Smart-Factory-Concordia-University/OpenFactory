import os
from mtcadapter.adapters import MTCAdapter
from mtcadapter.mtcdevices.sick import SIG350
from mtcadapter.mtcdevices.sick import SICK_IMC30_Sensor


class OFA_SIG350(SIG350):
    ip_address = os.getenv('SIG350_IP')
    sensors = {os.getenv('DEVICE_ALIAS'): SICK_IMC30_Sensor}


class SIG350_Adapter(MTCAdapter):
    adapter_port = 7878
    device_class = OFA_SIG350


def main():
    mmpadapter = SIG350_Adapter()
    mmpadapter.run()


if __name__ == "__main__":
    main()
