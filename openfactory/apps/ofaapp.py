import time
from openfactory.utils.assets import register_asset, deregister_asset
from openfactory.assets import Asset, AssetAttribute
import openfactory.config as config


class OpenFactoryApp(Asset):
    """
    Generic OpenFactory App
    """

    def __init__(self, app_uuid, ksqldb_url=config.KSQLDB, bootstrap_servers=config.KAFKA_BROKER):
        """
        Initialize the OpenFactory App
        """
        register_asset(app_uuid, "OpenFactoryApp", ksqldb_url=ksqldb_url, bootstrap_servers=bootstrap_servers)
        super().__init__(app_uuid, ksqldb_url, bootstrap_servers)

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

        except KeyboardInterrupt:
            print("Stopping app ...")
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
