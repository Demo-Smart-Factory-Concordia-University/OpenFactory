import docker
from typing import List
from sqlalchemy import event
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from .base import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .node import Node


class DockerContainer(Base):
    """
    Docker container
    """

    __tablename__ = "docker_container"

    id: Mapped[int] = mapped_column(primary_key=True)
    node_id = mapped_column(ForeignKey("ofa_nodes.id"))
    node: Mapped["Node"] = relationship(back_populates="containers")
    image: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(20), unique=True)
    command: Mapped[str] = mapped_column(String(40),
                                         default='')
    environment: Mapped[List["EnvVar"]] = relationship(back_populates="container",
                                                       cascade="all, delete-orphan")
    ports: Mapped[List["Port"]] = relationship(back_populates="container",
                                               cascade="all, delete-orphan")

    def __repr__(self):
        return f"Container (id={self.id} name={self.name})"

    @hybrid_property
    def docker_url(self):
        """ docker_url from node on which container is deployed """
        return self.node.docker_url

    @hybrid_property
    def network(self):
        """ network from node on which container is deployed """
        return self.node.network

    @hybrid_property
    def status(self):
        """ Status of container """
        client = docker.DockerClient(base_url=self.docker_url)
        container = client.containers.get(self.name)
        status = container.attrs['State']['Status']
        client.close()
        return status

    def start(self):
        """ Start Docker container """
        docker_client = docker.DockerClient(base_url=self.docker_url)
        container = docker_client.containers.get(self.name)
        container.start()
        docker_client.close()

    def stop(self):
        """ Stop Docker container """
        docker_client = docker.DockerClient(base_url=self.docker_url)
        container = docker_client.containers.get(self.name)
        container.stop()
        docker_client.close()


@event.listens_for(DockerContainer, 'after_insert')
def dockerContainer_after_insert(mapper, connection, target):
    """
    Create Docker container after a database object is inserted
    """
    ports_dict = {}
    for p in target.ports:
        ports_dict[p.container_port] = p.host_port
    env = []
    for var in target.environment:
        env.append(f"{var.variable}={var.value}")

    docker_client = docker.DockerClient(base_url=target.docker_url)
    docker_client.containers.create(target.image,
                                    name=target.name,
                                    detach=True,
                                    environment=env,
                                    ports=ports_dict,
                                    command=target.command,
                                    network=target.network)
    docker_client.close()


@event.listens_for(DockerContainer, 'after_delete')
def dockerContainer_after_delete(mapper, connection, target):
    """
    Remove Docker container when database object is deleted
    """
    docker_client = docker.DockerClient(base_url=target.docker_url)
    container = docker_client.containers.get(target.name)
    container.stop()
    container.remove()
    docker_client.close()


class EnvVar(Base):
    """
    Environment variables for a Docker container
    """

    __tablename__ = "container_envVars"

    id: Mapped[int] = mapped_column(primary_key=True)
    variable: Mapped[str] = mapped_column(String(20))
    value: Mapped[str] = mapped_column(String(20))
    container_id = mapped_column(ForeignKey("docker_container.id"))
    container: Mapped["DockerContainer"] = relationship(back_populates="environment")

    def __repr__(self):
        return f"Environment variable (id={self.id} variable={self.variable} value={self.value})"


class Port(Base):
    """
    Port for a Docker container
    """

    __tablename__ = "container_ports"

    id: Mapped[int] = mapped_column(primary_key=True)
    container_port: Mapped[str] = mapped_column(String(20))
    host_port: Mapped[int] = mapped_column(Integer())
    container_id = mapped_column(ForeignKey("docker_container.id"))
    container: Mapped["DockerContainer"] = relationship(back_populates="ports")

    def __repr__(self):
        return f"Port (id={self.id} container_port={self.host_port} value={self.host_port})"
