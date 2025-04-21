import time
import os
from openfactory.apps import OpenFactoryApp
from openfactory.kafka import KSQLDBClient


class TestApp(OpenFactoryApp):
    """
    Mocked Test Application to be deployed on an OpenFactory cluster
    """

    def main_loop(self):
        print("I am the main loop of the app.\nI don't do anything usefull.")
        counter = 1
        while True:
            print(counter)
            counter += 1
            time.sleep(2)

    def app_event_loop_stopped(self):
        """
        Close connection to ksqlDB server
        Not absolutely required as it is already done by KSQLDBClient class
        """
        self.ksql.close()


app = TestApp(
    app_uuid='TEST-APP',
    ksqlClient=KSQLDBClient(
            ksqldb_url=os.environ.get("KSQLDB_URL", "http://localhost:8088"),
            loglevel=os.environ.get("KSQLDB_LOG_LEVEL", "WARNING")),
    bootstrap_servers=os.environ.get("KAFKA_BROKER", "localhost:9092")
)
app.run()
