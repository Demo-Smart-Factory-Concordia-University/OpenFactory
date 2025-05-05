""" Tear down OpenFactory infrastructure. """

import docker
import openfactory.config as config
from typing import Dict
from openfactory.schemas.infra import get_infrastructure_from_config_file
from openfactory.models.user_notifications import user_notify
from openfactory.docker.docker_access_layer import dal
from openfactory.schemas.infra import Workers


def remove_workers(workers: Workers, node_ip_map: Dict[str, str]) -> None:
    """
    Removes worker nodes from the Docker Swarm cluster.

    This function:
    1. Drains each worker node by setting its availability to 'drain'.
    2. Remotely connects to the node and removes it from the Swarm.
    3. Removes the node from the cluster via the manager node.

    Args:
        workers (Dict[str, Dict[str, Any]]): A dictionary where keys are worker names and values
            contain node details including the 'ip' key.
        node_ip_map (Dict[str, str]): A mapping of IP addresses to Docker node IDs.
    """
    for name, details in workers.items():
        try:
            ip = str(details['ip'])
            if ip not in node_ip_map:
                continue

            # drain the node
            user_notify.info(f'Draining node {name} ...')
            node = dal.docker_client.nodes.get(node_ip_map.get(ip))
            node_spec = node.attrs['Spec']
            node_spec['Availability'] = 'drain'
            node.update(node_spec)

            # leave swarm on worker node
            user_notify.info(f'Removing node {name} from cluster ...')
            docker_url = f"ssh://{config.OPENFACTORY_USER}@{ip}"
            node_client = docker.DockerClient(base_url=docker_url)
            node_client.swarm.leave()

            # remove node on OpenFactory Manger Node
            dal.docker_client.api.remove_node(node_ip_map.get(ip), force=True)
            user_notify.success(f'Removed node {name}')

        except (docker.errors.APIError) as err:
            user_notify.fail(f'Node "{name}" could not be removed. Error was:<br>"{err}"')


def remove_infrastack(stack_config_file: str) -> None:
    """
    Tears down an infrastructure stack based on a configuration file.

    This function reads a YAML file describing the infrastructure stack, identifies
    existing nodes in the Docker Swarm cluster by their IPs, and removes the worker
    nodes accordingly.

    Args:
        stack_config_file (str): Path to the YAML configuration file
            describing the infrastructure stack.
    """
    # Load yaml description file
    stack = get_infrastructure_from_config_file(stack_config_file)

    # map nodes by IP
    node_ip_map = {
        node.attrs['Status']['Addr']: node.id for node in dal.docker_client.nodes.list()
        }

    remove_workers(stack['nodes']['workers'], node_ip_map)
