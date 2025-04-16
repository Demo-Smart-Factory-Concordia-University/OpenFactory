import docker
import openfactory.config as config
from openfactory.exceptions import OFAException


class DockerAccesLayer:
    """
    Docker Access Layer (DAL) via the OpenFactory Manger Node
    """

    docker_client = None
    docker_url = None
    worker_token = None
    manager_token = None

    def connect(self):
        """ Connect to Docker engine via the OpenFactory Manger Node """
        self.docker_url = config.OPENFACTORY_MANAGER_NODE_DOCKER_URL
        self.ip = config.OPENFACTORY_MANAGER_NODE
        self.docker_client = docker.DockerClient(base_url=self.docker_url)
        if 'JoinTokens' not in self.docker_client.swarm.attrs:
            raise OFAException(f'Docker running on {config.OPENFACTORY_MANAGER_NODE_DOCKER_URL} is not in Swarm mode')
        self.worker_token = self.docker_client.swarm.attrs['JoinTokens']['Worker']
        self.manager_token = self.docker_client.swarm.attrs['JoinTokens']['Manager']

    def get_node_name_labels(self):
        """ Returns a list of all swarm node name labels """
        name_labels = []
        for node in self.docker_client.nodes.list():
            labels = node.attrs.get('Spec', {}).get('Labels', {})
            if 'name' in labels:
                name_labels.append(labels['name'])
        return name_labels

    def get_node_ip_addresses(self):
        """ Returns a list of all swarm node IP addresses """
        ip_addresses = []
        for node in self.docker_client.nodes.list():
            status = node.attrs.get('Status', {})
            ip_address = status.get('Addr')
            if ip_address:
                ip_addresses.append(ip_address)
        return ip_addresses


dal = DockerAccesLayer()
