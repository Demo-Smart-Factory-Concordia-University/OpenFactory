""" Dockerclient of an active and reachable swarm manager. """

import docker
import openfactory.config as config
from openfactory.docker.swarm_manager import swarm_manager
from typing import Optional


def swarm_manager_docker_client() -> Optional[docker.DockerClient]:
    """
    Returns the DockerClient for an active and reachable Swarm manager or None.

    Attempts to fetch the Swarm manager node. If found, it establishes
    a Docker client connection to that manager node using SSH. If no active manager
    node is found, it returns None.

    Returns:
        Optional[docker.DockerClient]: A DockerClient instance if a manager node
        is found, otherwise None.
    """
    node = swarm_manager()
    if node is None:
        return None

    docker_url = f"ssh://{config.OPENFACTORY_USER}@{node.attrs['Status']['Addr']}"
    return docker.DockerClient(base_url=docker_url)
