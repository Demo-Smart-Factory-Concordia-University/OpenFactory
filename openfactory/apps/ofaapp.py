import os
import signal
import time
from openfactory.utils.assets import deregister_asset
from openfactory.assets import Asset, AssetAttribute
import openfactory.config as config


class OpenFactoryApp(Asset):
    """
    Generic OpenFactory App
    """

    # Application version number
    APPLICATION_VERSION = os.getenv('APPLICATION_VERSION', 'latest')
    APPLICATION_MANUFACTURER = os.getenv('APPLICATION_MANUFACTURER', 'OpenFactory')
    APPLICATION_LICENSE = os.getenv('APPLICATION_LICENSE', 'BSD-3-Clause license')

    def __init__(self, app_uuid, ksqldb_url=config.KSQLDB, bootstrap_servers=config.KAFKA_BROKER):
        """
        Initialize the OpenFactory App
        """
        # get paramters from environment (set if deployed by ofa deployment tool)
        app_uuid = os.getenv('APP_UUID', app_uuid)
        super().__init__(app_uuid, ksqldb_url, bootstrap_servers)

        # attributes of the application
        self.add_attribute(
            attribute_id='application_version',
            asset_attribute=AssetAttribute(
                value=self.APPLICATION_VERSION,
                type='Events',
                tag='Application.Version'
            )
        )
        self.add_attribute(
            attribute_id='application_manufacturer',
            asset_attribute=AssetAttribute(
                value=self.APPLICATION_MANUFACTURER,
                type='Events',
                tag='Application.Manufacturer'
            )
        )
        self.add_attribute(
            attribute_id='application_license',
            asset_attribute=AssetAttribute(
                value=self.APPLICATION_LICENSE,
                type='Events',
                tag='Application.License'
            )
        )

        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def welcome_banner(self):
        """
        Welcome banner printed to stdout
        Can be redefined by children
        """
        print("--------------------------------------------------------------")
        print(f"Starting OpenFactory App {self.asset_uuid}")
        print("--------------------------------------------------------------")

    def app_event_loop_stopped(self):
        """ Called when main loop is stopped """
        pass

    def signal_handler(self, signum, frame):
        """ Handle SIGINT and SIGTERM signals """
        signal_name = signal.Signals(signum).name
        print(f"Received signal {signal_name}, stopping app gracefully ...")
        self.app_event_loop_stopped()
        deregister_asset(self.asset_uuid, ksqldb_url=self.ksqldb_url, bootstrap_servers=self.bootstrap_servers)
        exit(0)

    def main_loop(self):
        """"
        Main loop of OpenFactory App
        Must be implemented by children
        """
        raise NotImplementedError("Method 'event_loop' must be implemented")

    def run(self):
        """ Run the OpenFactory app """
        self.welcome_banner()
        self.add_attribute('avail', AssetAttribute(
            value='AVAILABLE',
            tag='Availability',
            type='Events'
        ))
        print("Starting main loop")
        try:
            self.main_loop()

        except Exception as e:
            print(f"An error occurred in the main_loop of the app: {e}")
            self.app_event_loop_stopped()
            deregister_asset(self.asset_uuid, ksqldb_url=self.ksqldb_url, bootstrap_servers=self.bootstrap_servers)


if __name__ == "__main__":

    class MyApp(OpenFactoryApp):
        """
        Example usage
        """

        def main_loop(self):
            # For actual use case, add here your logic of the app
            print("I am the main loop of the app.\nI don't do anything usefull in this example.")
            counter = 1
            while True:
                print(counter)
                counter += 1
                time.sleep(2)

    app = MyApp(
        app_uuid='DEMO-APP',
        ksqldb_url="http://localhost:8088",
        bootstrap_servers="localhost:9092"
    )
    app.run()
