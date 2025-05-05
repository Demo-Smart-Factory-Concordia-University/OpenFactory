""" Connect OpenFactory devices to InfluxDB. """

from sqlalchemy import select

from openfactory.schemas.devices import get_devices_from_config_file
from openfactory.models.agents import Agent
from openfactory.models.user_notifications import user_notify


def connect_devices_to_influxdb(db_session, yaml_config_file: str) -> None:
    """
    Connects OpenFactory devices to InfluxDB using a YAML configuration file.

    Args:
        db_session (Session): SQLAlchemy database session used to query for agents.
        yaml_config_file (str): Path to the YAML configuration file describing devices.
    """
    # load yaml description file
    devices = get_devices_from_config_file(yaml_config_file)
    if devices is None:
        return

    for dev_name, device in devices.items():
        user_notify.info(f"{dev_name}:")

        if device['influxdb'] is None:
            user_notify.info("  No influxdb definition")
            continue

        query = select(Agent).where(Agent.uuid == device['uuid'].upper() + '-AGENT')
        agent = db_session.execute(query).one_or_none()
        if agent is None:
            user_notify.info(f"Device {dev_name} does not exist in OpenFactory. It was not connected to InfluxDB")
            continue

        agent[0].create_influxdb_connector(device['influxdb'])
