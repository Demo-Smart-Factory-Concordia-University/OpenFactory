from openfactory import OpenFactoryManager
from openfactory.schemas.devices import get_devices_from_config_file
from openfactory.models.user_notifications import user_notify


def shut_down_devices_from_config_file(yaml_config_file):
    """
    Shut down devices based on a config file
    """

    # Load yaml description file
    devices = get_devices_from_config_file(yaml_config_file)
    if devices is None:
        return

    ofa = OpenFactoryManager()
    uuid_list = [device.asset_uuid for device in ofa.devices()]

    for dev_name, device in devices.items():
        user_notify.info(f"{dev_name}:")
        if not device['uuid'] in uuid_list:
            user_notify.info(f"No device {device['uuid']} deployed in OpenFactory")
            continue

        ofa.tear_down_device(device['uuid'])
