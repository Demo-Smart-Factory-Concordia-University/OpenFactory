""" OpenFactory Deployment Strategy Interface and Implementations. """
import docker
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from openfactory.docker.docker_access_layer import dal


class OpenFactoryServiceDeploymentStrategy(ABC):
    """ Abstract base class for OpenFactory service deployment strategies. """

    @abstractmethod
    def deploy(self, *,
               image: str,
               name: str,
               env: List[str],
               labels: Optional[Dict[str, str]] = None,
               command: Optional[str] = None,
               ports: Optional[Dict[int, int]] = None,
               networks: Optional[List[str]] = None,
               constraints: Optional[List[str]] = None,
               resources: Optional[Dict[str, Any]] = None,
               mode: Optional[Dict[str, Any]] = None) -> None:
        """
        Deploy a service using the specified parameters.

        Args:
            image (str): Docker image to deploy.
            name (str): Name of the service or container.
            env (List[str]): Environment variables in `KEY=VALUE` format.
            labels (Optional[Dict[str, str]]): Metadata labels (Swarm only).
            command (Optional[str]): Command to override the default entrypoint.
            ports (Optional[Dict[int, int]]): Port mappings from host to container (host:container).
            networks (Optional[List[str]]): Networks to connect the service or container to.
            constraints (Optional[List[str]]): Constraints for placement (Swarm only).
            resources (Optional[Dict[str, Any]]): Resource limits and reservations.
            mode (Optional[Dict[str, Any]]): Service mode (Swarm only).
        """
        pass


class SwarmDeploymentStrategy(OpenFactoryServiceDeploymentStrategy):
    """ Deployment strategy for Docker Swarm mode. """

    def deploy(self, *,
               image: str,
               name: str,
               env: List[str],
               labels: Optional[Dict[str, str]] = None,
               command: Optional[str] = None,
               ports: Optional[Dict[int, int]] = None,
               networks: Optional[List[str]] = None,
               constraints: Optional[List[str]] = None,
               resources: Optional[Dict[str, Any]] = None,
               mode: Optional[Dict[str, Any]] = None) -> None:
        """
        Deploy a Docker service using Docker Swarm.

        See parent method for argument descriptions.
        """
        dal.docker_client.services.create(
            image=image,
            name=name,
            env=env,
            labels=labels,
            command=command,
            endpoint_spec=docker.types.EndpointSpec(ports=ports) if ports else None,
            networks=networks,
            constraints=constraints,
            resources=resources,
            mode=mode
        )


class LocalDockerDeploymentStrategy(OpenFactoryServiceDeploymentStrategy):
    """ Deployment strategy for local Docker containers (non-Swarm). """

    def deploy(self, *,
               image: str,
               name: str,
               env: List[str],
               labels: Optional[Dict[str, str]] = None,
               command: Optional[str] = None,
               ports: Optional[Dict[int, int]] = None,
               networks: Optional[List[str]] = None,
               constraints: Optional[List[str]] = None,
               resources: Optional[Dict[str, Any]] = None,
               mode: Optional[Dict[str, Any]] = None) -> None:
        """
        Run a local Docker container.

        See parent method for argument descriptions.

        Note:
            - Only the first network in the list is used.
            - `constraints` and `mode` are ignored for local containers.
        """
        dal.docker_client.containers.run(
            image=image,
            name=name,
            environment=env,
            command=command,
            detach=True,
            ports={f"{container_port}/tcp": host_port for host_port, container_port in ports.items()} if ports else None,
            network=networks[0] if networks else None,
            labels=labels,
            nano_cpus=resources.get("Limits", {}).get("NanoCPUs") if resources else None
        )
