""" Generic OpenFactory application. """

import os
import signal
import time
from typing import Optional
from openfactory.utils.assets import deregister_asset
from openfactory.assets import Asset, AssetAttribute
import openfactory.config as config


class OpenFactoryApp(Asset):
    """
    Generic OpenFactory application.

    Inherits from the `Asset` class and provides specific functionality related to an OpenFactory application, 
    including managing application-specific attributes and handling termination signals.

    Attributes:
        APPLICATION_VERSION (str): The version of the application, fetched from environment variable `APPLICATION_VERSION` or set to 'latest'.
        APPLICATION_MANUFACTURER (str): The manufacturer of the application, fetched from environment variable `APPLICATION_MANUFACTURER` or set to 'OpenFactory'.
        APPLICATION_LICENSE (str): The license type for the application, fetched from environment variable `APPLICATION_LICENSE` or set to 'BSD-3-Clause license'.

    Args:
        app_uuid (str): The UUID of the application (can be overridden by an environment variable `APP_UUID`).
        ksqlClient (KSQLDBClient): The KSQLDB client used for querying.
        bootstrap_servers (str): Kafka bootstrap servers (default is fetched from config).
    """

    # Application version number
    APPLICATION_VERSION = os.getenv('APPLICATION_VERSION', 'latest')
    APPLICATION_MANUFACTURER = os.getenv('APPLICATION_MANUFACTURER', 'OpenFactory')
    APPLICATION_LICENSE = os.getenv('APPLICATION_LICENSE', 'BSD-3-Clause license')

    def __init__(self, app_uuid: str, ksqlClient, bootstrap_servers: str = config.KAFKA_BROKER):
        """
        Initializes the OpenFactory application.
        
        Fetches the application's UUID from either the argument or the environment variable `APP_UUID`. It also sets up
        attributes for version, manufacturer, and license, and registers signal handlers for termination signals.

        Args:
            app_uuid (str): The UUID of the application (overrides the environment variable `APP_UUID` if provided).
            ksqlClient (KSQLDBClient): The KSQL client instance.
            bootstrap_servers (str): Kafka bootstrap server URL, default value is read from `config.KAFKA_BROKER`.

        """
        # get paramters from environment (set if deployed by ofa deployment tool)
        app_uuid = os.getenv('APP_UUID', app_uuid)
        super().__init__(app_uuid, ksqlClient=ksqlClient, bootstrap_servers=bootstrap_servers)

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

    def welcome_banner(self) -> None:
        """
        Welcome banner printed to stdout.

        Can be redefined by children
        """
        print("--------------------------------------------------------------")
        print(f"Starting OpenFactory App {self.asset_uuid}")
        print("--------------------------------------------------------------")

    def app_event_loop_stopped(self) -> None:
        """ Called when main loop is stopped. """
        pass

    def signal_handler(self, signum: int, frame: Optional[signal.FrameType]) -> None:
        """
        Handles SIGINT and SIGTERM signals, gracefully stopping the application.

        This method listens for termination signals, deregisters the asset from the system,
        and then stops the application’s event loop. It is typically used to handle clean
        shutdowns when the app receives signals like SIGINT or SIGTERM.

        Args:
            signum (int): The signal number that was received (e.g., SIGINT, SIGTERM).
            frame (Optional[signal.FrameType]): The current stack frame when the signal was received.
                This can be used for debugging or inspecting the state of the process.
        """
        signal_name = signal.Signals(signum).name
        print(f"Received signal {signal_name}, stopping app gracefully ...")
        deregister_asset(self.asset_uuid, ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers)
        self.app_event_loop_stopped()
        exit(0)

    def main_loop(self) -> None:
        """
        Main loop of the OpenFactory App.

        This method must be implemented by child classes to define the main
        application loop behavior. It will be responsible for managing the
        application's lifecycle, handling events, and maintaining any necessary
        state while the application is running.

        Raises:
            NotImplementedError: If this method is not implemented by a subclass.
        """
        raise NotImplementedError("Method 'event_loop' must be implemented")

    def run(self) -> None:
        """
        Runs the OpenFactory app.

        This method initializes the app by displaying a welcome banner, adding
        an availability attribute, and then starts the main application loop by
        calling `main_loop`. If an exception occurs during the execution of the
        main loop, the error is caught, and the app is gracefully stopped.

        The following steps are performed:
        1. Display the welcome banner.
        2. Add the 'avail' attribute with 'AVAILABLE' value.
        3. Start the main loop.
        4. Catch any exceptions that occur and stop the app gracefully.

        Raises:
            Exception: If any exception occurs during the execution of the main loop,
            it is caught and logged, and the app is stopped.
        """
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
            deregister_asset(self.asset_uuid, ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers)


if __name__ == "__main__":

    # Example usage of the OpenFactoryApp
    from openfactory.kafka import KSQLDBClient
    ksql = KSQLDBClient("http://localhost:8088")

    class MyApp(OpenFactoryApp):
        """ Example Application. """

        def main_loop(self):
            """ Main loop. """
            # For actual use case, add here your logic of the app
            print("I am the main loop of the app.\nI don't do anything usefull in this example.")
            counter = 1
            while True:
                print(counter)
                counter += 1
                time.sleep(2)

        def app_event_loop_stopped(self):
            """
            Close connection to ksqlDB server.

            Not absolutely required as it is already done by KSQLDBClient class
            """
            self.ksql.close()

    app = MyApp(
        app_uuid='DEMO-APP',
        ksqlClient=ksql,
        bootstrap_servers="localhost:9092"
    )
    app.run()
