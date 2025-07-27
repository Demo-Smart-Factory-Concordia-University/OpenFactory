""" OpenFactory Cluster Manager. """

import docker
import paramiko.ssh_exception
from socket import gaierror

from typing import Dict, Any
import openfactory.config as config
from openfactory.models.user_notifications import user_notify
from openfactory.docker.docker_access_layer import dal
from openfactory.schemas.infra import get_infrastructure_from_config_file
from openfactory.schemas.infra import Managers, Workers
from openfactory.exceptions import OFAException


class OpenFactoryCluster():
    """
    OpenFactory Cluster Manager.

    Allows to manage the OpenFactory cluster.

    Important:
        User requires Docker access on all nodes of the OpenFactory cluster
        and ssh access to all nodes using the config.OPENFACTORY_USER.
    """

    def __init__(self):
        """
        Initialize the OpenFactoryCluster instance.

        Performs a check to ensure the current Docker host is part of a Swarm
        and is a Swarm Manager. This is required for cluster management operations.

        Raises:
            OFAException: If the Docker host is not part of a Swarm, is not a manager,
                          or if the Swarm status cannot be verified.
        """
        try:
            info = dal.docker_client.info()
            if not info.get('Swarm', {}).get('LocalNodeState') == 'active':
                raise OFAException(f"Host {info['Name']} is not part of a Swarm.")
            if not info.get('Swarm', {}).get('ControlAvailable', False):
                raise OFAException(f"Node {info['Name']} is not a Swarm Manager.")
        except Exception as e:
            raise OFAException(str(e))

    def add_label(self, node_name: str, node_details: Dict[str, Any]) -> None:
        """
        Adds labels to a Docker node based on its IP address.

        Looks for a node in the Docker Swarm cluster whose IP address matches
        the given `node_details`. If found, it updates the node's labels by adding
        a 'name' label and merging any additional labels specified in `node_details`.

        Args:
            node_name (str): The name to assign as a label to the Docker node.
            node_details (Dict): Dictionary  with required 'ip' and optional 'labels' keys.

        Example:
            .. code-block:: python

                self.add_label("node-3", {"ip": "10.0.0.5", "labels": {"plant": "Plant-A", "role": "stream-apps"}})
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

    def create_managers(self, managers: Managers) -> None:
        """
        Creates Docker Swarm manager nodes from a given configuration.

        For each manager node in the input dictionary, connects via SSH, checks swarm membership,
        joins as a manager if needed, applies labels, and reports success or failure.

        Args:
            managers (Dict): Dictionary with manager names as keys and values as dicts with required 'ip' and optional 'labels'.

        Example:
            .. code-block:: python

                managers = {
                    "manager1": {"ip": "10.0.0.10", "labels": {"role": "primary"}},
                    "manager2": {"ip": "10.0.0.11"}
                }
                self.create_managers(managers)
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
                self.add_label(manager, details)
                user_notify.success(f'Node "{manager} ({ip})" setup')
            except (gaierror, paramiko.ssh_exception.NoValidConnectionsError, docker.errors.APIError) as err:
                user_notify.fail(f'Node "{manager}" could not be setup - {err}')

    def create_workers(self, workers: Workers) -> None:
        """
        Creates Docker Swarm worker nodes from a given configuration.

        Connects via SSH to each worker node, checks swarm membership, joins if needed,
        and applies labels.

        Args:
            workers (Dict): Dictionary with worker names as keys and values as dicts with required 'ip' and optional 'labels'.

        Example:
            .. code-block:: python

                workers = {
                    "worker1": {"ip": "10.0.0.20", "labels": {"role": "compute"}},
                    "worker2": {"ip": "10.0.0.21"}
                }
                self.create_workers(workers)
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
                self.add_label(worker, details)
                user_notify.success(f'Node "{worker} ({ip})" setup')
            except (gaierror, paramiko.ssh_exception.NoValidConnectionsError, docker.errors.APIError, docker.errors.DockerException) as err:
                user_notify.fail(f'Node "{worker}" could not be setup - {err}')

    def create_infrastack_from_config_file(self, stack_config_file: str) -> None:
        """
        Spins up an infrastructure stack based on the provided configuration file.

        Reads a YAML configuration file that defines the infrastructure,
        including manager and worker nodes, and provisions them using Docker Swarm.

        Args:
            stack_config_file (str): Path to the YAML configuration file describing the infrastructure stack.
        """
        infra = get_infrastructure_from_config_file(stack_config_file)

        if 'nodes' in infra:
            if infra['nodes']['managers']:
                self.create_managers(infra['nodes']['managers'])
            if infra['nodes']['workers']:
                self.create_workers(infra['nodes']['workers'])

    def remove_workers(self, workers: Workers, node_ip_map: Dict[str, str]) -> None:
        """
        Removes worker nodes from the Docker Swarm cluster.

        Drains each worker node, connects remotely to remove it from the Swarm,
        and removes the node from the cluster manager.

        Args:
            workers (Dict): Dictionary with worker names as keys and values containing node details with required 'ip'.
            node_ip_map (Dict): Mapping from node IP addresses to Docker node IDs.

        Example:
            .. code-block:: python

                workers = {
                    "worker1": {"ip": "10.0.0.20"},
                    "worker2": {"ip": "10.0.0.21"}
                }
                node_ip_map = {
                    "10.0.0.20": "node_id_123",
                    "10.0.0.21": "node_id_456"
                }
                self.remove_workers(workers, node_ip_map)
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

    def remove_infrastack_from_config_file(self, stack_config_file: str) -> None:
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

        self.remove_workers(stack['nodes']['workers'], node_ip_map)
