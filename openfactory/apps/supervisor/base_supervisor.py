""" OpenFactory Base Supervisor. """

from typing import Any
from openfactory.kafka import KafkaCommandsConsumer, KSQLDBClient
from openfactory.assets import Asset, AssetAttribute
from openfactory.apps import OpenFactoryApp
import openfactory.config as config


class BaseSupervisor(OpenFactoryApp):
    """
    Generic OpenFactory Supervisor application.

    Extends `OpenFactoryApp` to represent a supervisor that monitors or manages a specific device.
    It registers the device UUID it supervises as an asset attribute.

    Attributes:
        _device_uuid (str): The UUID of the device being supervised.
    """

    def __init__(self,
                 supervisor_uuid: str,
                 device_uuid: str,
                 ksqlClient: KSQLDBClient,
                 bootstrap_servers: str = config.KAFKA_BROKER,
                 loglevel: str = 'INFO'):
        """
        Initializes the BaseSupervisor.

        Args:
            supervisor_uuid (str): UUID of the supervisor application instance.
            device_uuid (str): UUID of the device that this supervisor monitors or controls.
            ksqlClient (KSQLDBClient): Instance of the KSQLDB client for streaming interaction.
            bootstrap_servers (str): Kafka broker address(es). Defaults to the value from config.
            loglevel (str): Logging level for the supervisor (e.g., 'INFO', 'DEBUG'). Defaults to 'INFO'.
        """
        super().__init__(app_uuid=supervisor_uuid,
                         ksqlClient=ksqlClient,
                         bootstrap_servers=bootstrap_servers,
                         loglevel=loglevel)

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

    def available_commands(self) -> list[str]:
        """
        Returns the list of commands handled by the supervisor.

        Must be implemented by subclasses to specify which commands they are capable of handling.

        Returns:
            List[str]: A list of command names as strings.

        Example return value:
            .. code-block:: json

                [
                    {"command": "start_device", "description": "Starts the device"},
                    {"command": "stop_device", "description": "Stops the device"}
                ]

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """
        raise NotImplementedError("You must implement the 'available_commands' method.")

    def _send_available_commands(self) -> None:
        """
        Sends the list of available commands to the target device asset.

        Retrieves the list of commands from `available_commands()`, and publishes them as attributes to the Asset it supervises.

        Each command is expected to be a dictionary with:
            - 'command' (str): The command name.
            - 'description' (str): A human-readable description of the command.

        Raises:
            KeyError: If a command dictionary is missing required keys.
        """
        dev = Asset(asset_uuid=self._device_uuid, ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers)
        for cmd in self.available_commands():
            dev.add_attribute(
                attribute_id=cmd['command'],
                asset_attribute=AssetAttribute(
                    value=cmd['description'],
                    type='Method',
                    tag='Method'
                )
            )
            self.logger.info(f"Sent method: [{cmd['command']} | {cmd['description']}]")

    def on_command(self, msg_key: str, msg_value: dict[str, Any]) -> None:
        """
        Callback method to process received commands.

        This method must be implemented by subclasses. It is called whenever
        a command message is received for the device associated with this supervisor.

        Args:
            msg_key (str): The key of the Kafka message (asset_uuid of the target Asset).
            msg_value (dict): Dictionary with required keys 'CMD' (command string) and 'ARGS' (space-separated args).

        Raises:
            NotImplementedError: If the method is not overridden in a subclass.

        Example:
            .. code-block:: python

                self.on_command(
                    "DEVICE-123",
                    {"CMD": "reset", "ARGS": "--force --timeout 10"}
                )
        """
        raise NotImplementedError("You must implement the 'on_command' method.")

    def main_loop(self) -> None:
        """
        Main loop of the Supervisor.

        Performs the following:
        1. Sends the list of available commands to the supervised device.
        2. Initializes a Kafka command consumer subscribed to the command stream for the device.
        3. Starts consuming command messages and delegates handling to the `on_command` method.
        """
        # sends commands to device_uuid that supervisor is handling
        self._send_available_commands()

        kakfa_group_id = self.asset_uuid + '-SUPERVISOR-GROUP'

        cmd_consumer = KafkaCommandsConsumer(
            consumer_group_id=kakfa_group_id,
            asset_uuid=self._device_uuid,
            on_command=self.on_command,
            ksqlClient=self.ksql,
            bootstrap_servers=self.bootstrap_servers)

        cmd_consumer.consume()


if __name__ == "__main__":

    # Example usage of BaseSupervisor class
    from openfactory.kafka import KSQLDBClient
    ksql = KSQLDBClient("http://localhost:8088")

    class DemoSupervisor(BaseSupervisor):
        """ Demo class. """

        def available_commands(self):
            """ This demo supervisor handles a fake demo_cmd. """
            return [{
                "command": "demo_cmd",
                "description": "This is for demo only. This command does nothing"
                }]

        def on_command(self, msg_key, msg_value):
            """ Callback to process received commands. """
            print(f"[{msg_key}] {msg_value}")

        def app_event_loop_stopped(self):
            """
            Close connection to ksqlDB server.

            Not absolutely required as it is already done by KSQLDBClient class
            """
            self.ksql.close()

    supervisor = DemoSupervisor(
        supervisor_uuid='DEMO-SUPERVISOR',
        device_uuid='PROVER3018',
        ksqlClient=ksql,
        bootstrap_servers="localhost:9092"
    )

    supervisor.run()
