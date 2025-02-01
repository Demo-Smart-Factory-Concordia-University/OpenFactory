from sqlalchemy import select
from openfactory.exceptions import OFAException
from openfactory.schemas.devices import get_devices_from_config_file
from openfactory.models.user_notifications import user_notify
from openfactory.models.agents import Agent
from openfactory.factories.remove_supervisor import remove_device_supervisor


def remove_devices_from_config_file(db_session, yaml_config_file):
    """
    Removes devices based on a config file
    """

    # Load yaml description file
    devices = get_devices_from_config_file(yaml_config_file)
    if devices is None:
        return

    for dev_name, device in devices.items():
        user_notify.info(f"{dev_name}:")
        agent_uuid = device['uuid'].upper() + "-AGENT"
        query = select(Agent).where(Agent.uuid == agent_uuid)
        agent = db_session.execute(query).one_or_none()
        if agent is None:
            user_notify.info(f'No Agent {agent_uuid} defined in OpenFactory')
            continue
        try:
            db_session.delete(agent[0])
            db_session.commit()
        except OFAException as err:
            db_session.rollback()
            user_notify.fail(f"Cannot remove {device['uuid']} - {err}")
        if device['supervisor']:
            remove_device_supervisor(device)
        user_notify.success(f"{device['uuid']} removed successfully")
