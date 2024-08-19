import docker
import docker.errors
import openfactory.config as config
from openfactory.docker.docker_access_layer import dal
from openfactory.models.user_notifications import user_notify
from openfactory.utils import load_yaml


def create_managers(managers):
    """ Create manager nodes """
    for name, ip in managers.items():
        try:
            docker_url = f"ssh://{config.OPENFACTORY_USER}@{ip}"
            client = docker.DockerClient(base_url=docker_url)
            info = client.info()
            if 'Swarm' in info and info['Swarm']['NodeID']:
                continue
            client.swarm.join([dal.ip], join_token=dal.manager_token)
            user_notify.success(f'Node "{name} ({ip})" setup')
        except (docker.errors.APIError) as err:
            user_notify.fail(f'Node "{name}" could not be setup. Error was:<br>"{err}"')


def create_workers(workers):
    """ Create worker nodes """
    for name, ip in workers.items():
        try:
            docker_url = f"ssh://{config.OPENFACTORY_USER}@{ip}"
            client = docker.DockerClient(base_url=docker_url)
            info = client.info()
            if 'Swarm' in info and info['Swarm']['NodeID']:
                continue
            client.swarm.join([dal.ip], join_token=dal.worker_token)
            user_notify.success(f'Node "{name} ({ip})" setup')
        except (docker.errors.APIError) as err:
            user_notify.fail(f'Node "{name}" could not be setup. Error was:<br>"{err}"')


def create_infrastack(stack_config_file):
    """
    Spins up an infrastructure stack
    """

    # Load yaml description file
    infra = load_yaml(stack_config_file)

    create_managers(infra['nodes']['managers'])
    create_workers(infra['nodes']['workers'])
