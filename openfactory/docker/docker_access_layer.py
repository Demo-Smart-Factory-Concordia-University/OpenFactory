""" Docker Access Layer. """

import docker
import openfactory.config as config
from openfactory.exceptions import OFAException
from typing import List, Optional


class DockerAccesLayer:
    """
    Docker Access Layer (DAL) for interfacing with the Docker Swarm cluster.

    Provides methods to connect to the Docker daemon, retrieve swarm join tokens,
    and fetch information such as node labels and IP addresses.
    """

    def __init__(self) -> None:
        """
        Initializes the DockerAccesLayer with empty connection state.

        Attributes:
            docker_client (Optional[docker.DockerClient]): The Docker client used to communicate with the manager node.
            docker_url (Optional[str]): The URL used to connect to the Docker daemon.
            worker_token (Optional[str]): The token used for joining workers to the Swarm.
            manager_token (Optional[str]): The token used for joining managers to the Swarm.
            ip (Optional[str]): IP address of the OpenFactory manager node.
        """
        self.docker_client: Optional[docker.DockerClient] = None
        self.docker_url: Optional[str] = None
        self.worker_token: Optional[str] = None
        self.manager_token: Optional[str] = None
        self.ip: Optional[str] = None

    def connect(self) -> None:
        """
        Connects to the Docker engine via the OpenFactory Manager Node.

        Sets up the Docker client, verifies that the manager node is in swarm mode,
        and retrieves the join tokens for workers and managers.

        Raises:
            OFAException: If the Docker instance is not part of a swarm cluster.
        """
        self.docker_url = config.OPENFACTORY_MANAGER_NODE_DOCKER_URL
        self.ip = config.OPENFACTORY_MANAGER_NODE
        self.docker_client = docker.DockerClient(base_url=self.docker_url)
        if 'JoinTokens' not in self.docker_client.swarm.attrs:
            raise OFAException(f'Docker running on {config.OPENFACTORY_MANAGER_NODE_DOCKER_URL} is not in Swarm mode')
        self.worker_token = self.docker_client.swarm.attrs['JoinTokens']['Worker']
        self.manager_token = self.docker_client.swarm.attrs['JoinTokens']['Manager']

    def get_node_name_labels(self) -> List[str]:
        """
        Retrieves the 'name' labels for all nodes in the swarm cluster.

        Returns:
            List[str]: A list of node names from the swarm.
        """
        name_labels = []
        for node in self.docker_client.nodes.list():
            labels = node.attrs.get('Spec', {}).get('Labels', {})
            if 'name' in labels:
                name_labels.append(labels['name'])
        return name_labels

    def get_node_ip_addresses(self) -> List[str]:
        """
        Retrieves the IP addresses of all nodes in the swarm cluster.

        Returns:
            List[str]: A list of IP addresses from the swarm nodes.
        """
        ip_addresses = []
        for node in self.docker_client.nodes.list():
            status = node.attrs.get('Status', {})
            ip_address = status.get('Addr')
            if ip_address:
                ip_addresses.append(ip_address)
        return ip_addresses


dal = DockerAccesLayer()
