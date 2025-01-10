import asyncio
from openfactory.apps.ofaapp import OpenFactoryApp


class SinkConnector(OpenFactoryApp):
    """
    OpenFactory Generic Sink Connector
    """

    def __init__(self, connector_uuid: str, service_stream: str, ksql_url: str):
        """
        Initialize the Sink Connector

        :param connector_uuid: UUID of the sink connector
        :param service_stream: ksqlDB stream for which this connector operates
        :param ksql_url: URL of the ksqlDB server
        """
        self.service_stream = service_stream
        super().__init__(app_uuid=connector_uuid, ksql_url=ksql_url)

        # store event loop
        self._event_loop = asyncio.get_event_loop()

    def welcome_banner(self):
        """
        Welcome banner printed to stdout
        """
        print("--------------------------------------------------------------")
        print(f"Starting OpenFactory sink connector for {self.service_stream}")
        print("--------------------------------------------------------------")

    def send_inital_msg(self):
        """ Send inital message to ksqlDB when App is started """
        msg = [
            {
                "device_uuid": self.app_uuid,
                "id": "service_uuid",
                "value": self.service_stream,
                "tag": 'StreamUuid',
                "type": 'Events'
            }
        ]
        return msg

    def stream_query(self):
        """ Return query for service stream. Can be redefined by children """
        return f"SELECT * FROM {self.service_stream} EMIT CHANGES;"

    async def main_loop(self):
        """ Fetch streaming data from the ksqlDB stream of the OpenFactory device """
        try:
            await self.ksql.query(
                query=self.stream_query(),
                earliest=False,
                on_new_row=lambda row: asyncio.create_task(self.new_data(row))
            )
        except asyncio.CancelledError:
            # Handle cancellation due to shutdown signal
            print('Sink connector is shutdown')
            return
        except Exception as e:
            print(f"An error occurred: {e}")
        print(f"ERROR - ksqlDB query for stream {self.service_stream} terminated.\nDoes this stream exist ?")

    async def new_data(self, data):
        """
        Handle a new data

        :param data: The data received from the ksqlDB device stream
        """
        raise NotImplementedError("You must implement the 'new_data' method.")


class MySinkConnector(SinkConnector):
    """
    Example usage
    """
    async def new_data(self, data):
        # For actual use case, add here your logic to process the fetched data
        print(f"Handling data from {self.service_stream}: {data}")

    def send_inital_msg(self):
        """ Sends additonal inital message at start """
        msg = [
            {
                "device_uuid": self.app_uuid,
                "id": "version",
                "value": "1.0",
                "tag": "Version",
                "type": 'Events'
            }
        ]
        return msg + super().send_inital_msg()


if __name__ == "__main__":
    """ runs as: python -m openfactory.apps.connectors.sinkconnector """
    connector = MySinkConnector(
        connector_uuid='ZAIX-001-CONNECTOR',
        service_stream="ZAIX_001_STREAM",
        ksql_url="http://localhost:8088"
    )
    connector.run()
