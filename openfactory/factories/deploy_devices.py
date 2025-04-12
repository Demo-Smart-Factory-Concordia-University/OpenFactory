import os
from fsspec.core import split_protocol
from openfactory import OpenFactoryManager
from openfactory.schemas.devices import get_devices_from_config_file
from openfactory.models.user_notifications import user_notify
from openfactory.utils import register_asset


def deploy_devices_from_config_file(yaml_config_file, ksqlClient):
    """
    Deploy OpenFactory devices based on a yaml configuration file
    """

    # load yaml description file
    devices = get_devices_from_config_file(yaml_config_file)
    if devices is None:
        return

    ofa = OpenFactoryManager(ksqlClient=ksqlClient)

    for dev_name, device in devices.items():
        user_notify.info(f"{dev_name}:")
        if device['uuid'] in ofa.devices_uuid():
            user_notify.info(f"Device {device['uuid']} exists already and was not deployed")
            continue

        # compute device device xml uri
        if device['agent']['ip']:
            device_xml_uri = ""
        else:
            device_xml_uri = device['agent']['device_xml']
            protocol, _ = split_protocol(device_xml_uri)
            if not protocol:
                if not os.path.isabs(device_xml_uri):
                    device_xml_uri = os.path.join(os.path.dirname(yaml_config_file), device_xml_uri)

        register_asset(device['uuid'], "Device", ksqlClient=ksqlClient, docker_service="")

        ofa.deploy_mtconnect_agent(device_uuid=device['uuid'],
                                   device_xml_uri=device_xml_uri,
                                   agent=device['agent'])

        ofa.deploy_kafka_producer(device)

        if device['ksql_tables']:
            ofa.create_device_ksqldb_tables(device_uuid=device['uuid'],
                                            ksql_tables=device['ksql_tables'])

        if device['supervisor']:
            ofa.deploy_device_supervisor(device_uuid=device['uuid'],
                                         supervisor=device['supervisor'])

        user_notify.success(f"Device {device['uuid']} deployed successfully")
