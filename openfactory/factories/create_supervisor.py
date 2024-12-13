import docker
import openfactory.config as config
from openfactory.docker.docker_access_layer import dal
from openfactory.models.user_notifications import user_notify


def get_nested(data, keys, default=None):
    """ Get safely a nested value from a dictionary """
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data


def deploy_device_supervisor(device):
    """
    Deploy an OpenFactory device supervisor
    """

    if device['supervisor'] is None:
        return

    # get ressources if any were defined
    cpus_reservation = get_nested(device, ['supervisor', 'deploy', 'resources', 'reservations', 'cpus'], 0.5)
    cpus_limit = get_nested(device, ['supervisor', 'deploy', 'resources', 'limits', 'cpus'], 1)

    # build environment variables
    env = [f"DEVICE_UUID={device['uuid']}",
           f"KSQL_URL={config.KSQLDB}",
           f"ADAPTER_IP={device['supervisor']['adapter']['ip']}",
           f"ADAPTER_PORT={device['supervisor']['adapter']['port']}"]

    if device['supervisor']['adapter']['environment'] is not None:
        for item in device['supervisor']['adapter']['environment']:
            var, val = item.split('=')
            env.append(f"{var.strip()}={val.strip()}")

    client = dal.docker_client
    try:
        client.services.create(
            image=device['supervisor']['image'],
            name=device['uuid'].lower() + '-supervisor',
            mode={"Replicated": {"Replicas": 1}},
            env=env,
            networks=[config.OPENFACTORY_NETWORK],
            resources={
                "Limits": {"NanoCPUs": int(1000000000*cpus_limit)},
                "Reservations": {"NanoCPUs": int(1000000000*cpus_reservation)}
                }
        )
    except docker.errors.APIError as err:
        user_notify.fail(f"Supervisor {device['uuid'].lower()}-supervisor could not be created\n{err}")
        return
    user_notify.success(f"Supervisor {device['uuid'].lower()}-supervisor started successfully")
    user_notify.success(f"ksqlDB stream {device['uuid'].upper().replace('-', '_')}_CMDS_STREAM created successfully")
    user_notify.success(f"ksqlDB tables {device['uuid'].upper().replace('-', '_')}_CMDS and {device['uuid'].upper().replace('-', '_')}_SUPERVISOR created successfully")
