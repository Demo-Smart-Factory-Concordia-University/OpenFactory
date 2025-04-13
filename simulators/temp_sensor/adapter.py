import time
import random
import os
from mtcadapter.mtcdevices import MTCDevice
from mtcadapter.adapters import MTCAdapter


class MockedTemperatureSensor(MTCDevice):

    SLEEP_INTERVAL = float(os.environ.get("SLEEP_INTERVAL", 3.0))
    MIN_TEMP = float(os.environ.get("MIN_TEMP", 18))
    MAX_TEMP = float(os.environ.get("MAX_TEMP", 22))

    def read_data(self):
        time.sleep(self.SLEEP_INTERVAL)
        data = {'Temp': round(random.uniform(self.MIN_TEMP, self.MAX_TEMP), 2)}
        return data


class MockedTemperaturSensorAdapter(MTCAdapter):
    device_class = MockedTemperatureSensor
    adapter_port = int(os.environ.get("ADAPTER_PORT", 7878))


def main():
    adapter = MockedTemperaturSensorAdapter()
    adapter.run()


if __name__ == "__main__":
    main()
