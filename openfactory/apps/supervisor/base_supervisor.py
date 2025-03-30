from openfactory.kafka import KafkaCommandsConsumer
from openfactory.assets import Asset, AssetAttribute
from openfactory.apps import OpenFactoryApp
import openfactory.config as config


class BaseSupervisor(OpenFactoryApp):
    """
    OpenFactory Device Command Supervisor
    """

    def __init__(self, supervisor_uuid: str, device_uuid: str,
                 ksqldb_url=config.KSQLDB, bootstrap_servers=config.KAFKA_BROKER):
        """
        Initialize the BaseSupervisor

        :param supervisor_uuid: UUID of the supervisor
        :param device_uuid: UUID of the device to listen for commands
        :param ksql_url: URL of the ksqlDB server
        :param bootstrap_servers: kafka broker of Kaka cluster
        """
        super().__init__(app_uuid=supervisor_uuid, ksqldb_url=ksqldb_url, bootstrap_servers=bootstrap_servers)

        self._device_uuid = device_uuid

        # attributes of supervisor
        self.add_attribute(
            attribute_id='device_added',
            asset_attribute=AssetAttribute(
                value=device_uuid,
                type='Events',
                tag='DeviceAdded'
            )
        )

    def available_commands(self):
        """ Return the list of commands handled by the supervisor """
        raise NotImplementedError("You must implement the 'available_commands' method.")

    def _send_available_commands(self):
        """ Send available commands to asset device_uuid """
        dev = Asset(asset_uuid=self._device_uuid, ksqldb_url=self.ksqldb_url, bootstrap_servers=self.bootstrap_servers)
        for cmd in self.available_commands():
            dev.add_attribute(
                attribute_id=cmd['command'],
                asset_attribute=AssetAttribute(
                    value=cmd['description'],
                    type='Method',
                    tag='Method'
                )
            )
            print(f"Sent method: [{cmd['command']} | {cmd['description']}]")

    def on_command(self, msg_key, msg_value):
        """ Callback to process received commands """
        raise NotImplementedError("You must implement the 'on_command' method.")

    def main_loop(self):
        """ Main loop of Supervisor """

        # sends commands to device_uuid that supervisor is handling
        self._send_available_commands()

        kakfa_group_id = self.asset_uuid + '-SUPERVISOR-GROUP'

        cmd_consumer = KafkaCommandsConsumer(
            consumer_group_id=kakfa_group_id,
            asset_uuid=self._device_uuid,
            on_command=self.on_command,
            bootstrap_servers=self.bootstrap_servers,
            ksqldb_url=self.ksqldb_url)

        cmd_consumer.consume()


if __name__ == "__main__":

    # Example usage of BaseSupervisor class

    class DemoSupervisor(BaseSupervisor):

        def available_commands(self):
            """ This demo supervisor handles a fake demo_cmd """
            return [{
                "command": "demo_cmd",
                "description": "This is for demo only. This command does nothing"
                }]

        def on_command(self, msg_key, msg_value):
            """ Callback to process received commands """
            print(f"[{msg_key}] {msg_value}")

    supervisor = DemoSupervisor(
        supervisor_uuid='DEMO-SUPERVISOR',
        device_uuid='PROVER3018',
        ksqldb_url="http://localhost:8088",
        bootstrap_servers="localhost:9092"
    )

    supervisor.run()
