import docker
import docker.errors
import openfactory.config as config
import paramiko.ssh_exception
from socket import gaierror
from openfactory.docker.docker_access_layer import dal
from openfactory.models.user_notifications import user_notify
from openfactory.schemas.infra import get_infrastructure_from_config_file


def add_label(node_name, node_details):
    """ Adds the labels to the node """
    node = None
    for n in dal.docker_client.nodes.list():
        if node_details['ip'] in n.attrs['Status']['Addr']:
            node = n
            break
    if node is None:
        return

    # add labels
    labels = {'name': node_name}
    if 'labels' in node_details:
        labels.update(node_details['labels'])
    node_spec = node.attrs['Spec']
    node_spec['Labels'] = labels
    node.update(node_spec)


def create_managers(managers):
    """ Create manager nodes """
    for manager, details in managers.items():
        try:
            ip = details['ip']
            docker_url = f"ssh://{config.OPENFACTORY_USER}@{ip}"
            client = docker.DockerClient(base_url=docker_url)
            info = client.info()
            if 'Swarm' in info and info['Swarm']['NodeID']:
                continue
            client.swarm.join([dal.ip], join_token=dal.manager_token)
            add_label(manager, details)
            user_notify.success(f'Node "{manager} ({ip})" setup')
        except (gaierror, paramiko.ssh_exception.NoValidConnectionsError, docker.errors.APIError) as err:
            user_notify.fail(f'Node "{manager}" could not be setup - {err}')


def create_workers(workers):
    """ Create worker nodes """
    for worker, details in workers.items():
        try:
            ip = details['ip']
            docker_url = f"ssh://{config.OPENFACTORY_USER}@{ip}"
            client = docker.DockerClient(base_url=docker_url)
            info = client.info()
            if 'Swarm' in info and info['Swarm']['NodeID']:
                continue
            client.swarm.join([dal.ip], join_token=dal.worker_token)
            add_label(worker, details)
            user_notify.success(f'Node "{worker} ({ip})" setup')
        except (gaierror, paramiko.ssh_exception.NoValidConnectionsError, docker.errors.APIError, docker.errors.DockerException) as err:
            user_notify.fail(f'Node "{worker}" could not be setup - {err}')


def create_infrastack(stack_config_file):
    """
    Spins up an infrastructure stack
    """

    # Load yaml description file
    infra = get_infrastructure_from_config_file(stack_config_file)

    if 'nodes' in infra:
        if 'managers' in infra['nodes']:
            create_managers(infra['nodes']['managers'])
        if 'workers' in infra['nodes']:
            create_workers(infra['nodes']['workers'])
