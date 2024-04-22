import yaml
from sqlalchemy import select
from openfactory.models.user_notifications import user_notify
from openfactory.models.agents import Agent


def remove_devices_from_config_file(db_session, yaml_config_file):
    """
    Removes devices based on a config file
    """

    # Load yaml description file
    with open(yaml_config_file, 'r') as stream:
        cfg = yaml.safe_load(stream)

    for dev in cfg['devices']:
        device = cfg['devices'][dev]
        user_notify.info(f"{device['UUID']}:")
        agent_uuid = device['UUID'].upper() + "-AGENT"
        query = select(Agent).where(Agent.uuid == agent_uuid)
        agent = db_session.execute(query).one_or_none()
        if agent is None:
            user_notify.info(f'No Agent {agent_uuid} defined in OpenFactory')
            continue
        agent[0].stop()
        agent[0].detach()
        db_session.delete(agent[0])
        db_session.commit()
        user_notify.success(f"{device['UUID']} removed successfully")
