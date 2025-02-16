from openfactory.docker.docker_access_layer import dal
from openfactory.models.user_notifications import user_notify
from openfactory.utils.assets import deregister_asset


def remove_device_supervisor(device):
    """
    Tear down an OpenFactory device supervisor
    """

    if device['supervisor'] is None:
        return

    client = dal.docker_client
    supervisor_service = client.services.get(device['uuid'].lower() + '-supervisor')
    supervisor_service.remove()
    deregister_asset(f"{device['uuid'].upper()}-SUPERVISOR")
    user_notify.success(f"Supervisor {device['uuid'].upper()}-SUPERVISOR removed successfully")
