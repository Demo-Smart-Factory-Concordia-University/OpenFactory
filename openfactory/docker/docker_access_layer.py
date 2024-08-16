import docker
import openfactory.config as config


class DockerAccesLayer:
    """
    Docker Access Layer (DAL) via the OpenFactory Manger Node
    """

    docker_client = None
    docker_url = None

    def connect(self):
        """ Connect to Docker engine via the OpenFactory Manger Node """
        self.docker_url = f"ssh://{config.OPENFACTORY_USER}@{config.OPENFACTORY_MANAGER_NODE}"
        self.docker_client = docker.DockerClient(base_url=self.docker_url)


dal = DockerAccesLayer()
