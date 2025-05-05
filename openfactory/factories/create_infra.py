""" Create OpenFactory infrastructure. """

import docker
import docker.errors
import openfactory.config as config
import paramiko.ssh_exception
from socket import gaierror
from typing import Dict, Any
from openfactory.docker.docker_access_layer import dal
from openfactory.models.user_notifications import user_notify
from openfactory.schemas.infra import get_infrastructure_from_config_file
from openfactory.schemas.infra import Managers, Workers


def add_label(node_name: str, node_details: Dict[str, Any]) -> None:
    """
    Adds labels to a Docker node based on its IP address.

    Looks for a node in the Docker Swarm cluster whose IP address matches
    the given `node_details`. If found, it updates the node's labels by adding
    a 'name' label and merging any additional labels specified in `node_details`.

    Args:
        node_name (str): The name to assign as a label to the Docker node.
        node_details (Dict[str, Any]): A dictionary containing the IP address of the node
                                       under the 'ip' key and optionally additional labels
                                       under the 'labels' key.
    """
    node = None
    for n in dal.docker_client.nodes.list():
        if str(node_details['ip']) in n.attrs['Status']['Addr']:
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


def create_managers(managers: Managers) -> None:
    """
    Creates Docker Swarm manager nodes from a given configuration.

    For each manager node specified in the input dictionary, this function connects via SSH,
    checks if the node is already part of a Swarm, and if not, joins it to the Swarm as a manager.
    It also assigns appropriate labels to the node and notifies the user of success or failure.

    Args:
        managers (Dict[str, Dict[str, Any]]): A dictionary where keys are manager names and values
            are dictionaries containing at least the 'ip' key, and optionally a 'labels' key for node labels.
    """
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


def create_workers(workers: Workers) -> None:
    """
    Creates Docker Swarm worker nodes from a given configuration.

    For each worker node specified in the input dictionary, this function connects via SSH,
    checks if the node is already part of a Swarm, and if not, joins it as a worker. It then
    assigns appropriate labels.

    Args:
        workers (Dict[str, Dict[str, Any]]): A dictionary where keys are worker names and values
            are dictionaries containing at least the 'ip' key, and optionally a 'labels' key for node labels.
    """
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


def create_infrastack(stack_config_file: str) -> None:
    """
    Spins up an infrastructure stack based on the provided configuration file.

    Reads a YAML configuration file that defines the infrastructure,
    including manager and worker nodes, and provisions them using Docker Swarm.

    Args:
        stack_config_file (str): Path to the YAML configuration file
            describing the infrastructure stack.
    """
    infra = get_infrastructure_from_config_file(stack_config_file)

    if 'nodes' in infra:
        if infra['nodes']['managers']:
            create_managers(infra['nodes']['managers'])
        if infra['nodes']['workers']:
            create_workers(infra['nodes']['workers'])
