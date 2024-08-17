import docker
import openfactory.config as config
from .swarm_manager import swarm_manager


def swarm_manager_docker_client():
    """
    Returns the Dockerclient of an active and reachable swarm manager or None
    """
    node = swarm_manager()
    if node is None:
        return None

    docker_url = f"ssh://{config.OPENFACTORY_USER}@{node.attrs['Status']['Addr']}"
    return docker.DockerClient(base_url=docker_url)
