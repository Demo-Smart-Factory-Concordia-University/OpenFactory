import docker
import os
import tarfile
from requests.exceptions import ConnectionError
from paramiko.ssh_exception import NoValidConnectionsError, SSHException
from tempfile import TemporaryDirectory
from typing import List
import docker.errors
from sqlalchemy import event
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Double
from sqlalchemy import String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from .base import Base
from openfactory.exceptions import OFAException
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .nodes import Node


# Connections to Docker clients
_docker_clients = {}


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
    cpus = mapped_column(Double(), default=0)

    _status_error = None

    def __repr__(self):
        return f"Container (id={self.id} name={self.name})"

    @hybrid_property
    def docker_client(self):
        """ Return DockerClient to manage the container """
        if self.docker_url not in _docker_clients:
            _docker_clients[self.docker_url] = docker.DockerClient(base_url=self.docker_url)

        # check Docker engine can be reached
        try:
            _docker_clients[self.docker_url].ping()
        except ConnectionError:
            # re-establish connection in case socket was closed
            _docker_clients[self.docker_url] = docker.DockerClient(base_url=self.docker_url)
            # ping again
            # will raise an error in case connection still absent (to be handled by caller)
            _docker_clients[self.docker_url].ping()
        return _docker_clients[self.docker_url]

    @hybrid_property
    def docker_url(self):
        """ docker_url from node on which container is deployed """

        # TO BE DONE
        return None

    @hybrid_property
    def network(self):
        """ network from node on which container is deployed """

        # TO BE DONE
        return None

    @hybrid_property
    def container(self):
        """ Gets Docker container or None """
        try:
            container = self.docker_client.containers.get(self.name)
        except (docker.errors.DockerException):
            self._status_error = 'no container'
            return None
        except (ConnectionError, NoValidConnectionsError, SSHException):
            self._status_error = 'node down'
            return None
        self._status_error = None
        return container

    @hybrid_property
    def status(self):
        """ Status of container """
        if self.container:
            return self.container.attrs['State']['Status']
        else:
            return self._status_error

    def add_file(self, src, dest):
        """ Copy a file into the Docker container """
        tmp_dir = TemporaryDirectory()
        tmp_file = os.path.join(tmp_dir.name, 'files.tar')
        tar = tarfile.open(tmp_file, mode='w')
        try:
            tar.add(src, arcname=os.path.basename(dest))
        finally:
            tar.close()
        with open(tmp_file, 'rb') as f:
            data = f.read()
        if self.container:
            self.container.put_archive(os.path.dirname(dest), data)
        else:
            raise OFAException(f'Cannot add file to container - {self._status_error}')
        tmp_dir.cleanup()

    def start(self):
        """ Start Docker container """
        if self.container:
            self.container.start()
        else:
            raise OFAException(f'Cannot start container - {self._status_error}')

    def stop(self):
        """ Stop Docker container """
        if self.container:
            self.container.stop()
        else:
            raise OFAException(f'Cannot stop container - {self._status_error}')


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

    try:
        target.docker_client.images.get(target.image)
    except (ConnectionError, NoValidConnectionsError, SSHException):
        raise OFAException(f"Could not create container {target.name} - Node is down")
    except docker.errors.ImageNotFound:
        try:
            target.docker_client.images.pull(target.image)
        except docker.errors.ImageNotFound:
            raise OFAException(f"Could not find Docker image '{target.image}'")

    try:
        target.docker_client.containers.create(target.image,
                                               name=target.name,
                                               detach=True,
                                               environment=env,
                                               ports=ports_dict,
                                               command=target.command,
                                               network=target.network,
                                               nano_cpus=int(target.cpus*1E9))
    except docker.errors.DockerException as err:
        raise OFAException(f"Could not create container: {err}")


@event.listens_for(DockerContainer, 'after_delete')
def dockerContainer_after_delete(mapper, connection, target):
    """
    Remove Docker container when database object is deleted
    """
    try:
        container = target.docker_client.containers.get(target.name)
        container.stop()
        container.remove()
    except docker.errors.DockerException:
        # in case the container doesn't exist
        # (e.g. was removed by other ways than ofa)
        # ignore error and proceed with deleting database entry
        pass
    except (ConnectionError, SSHException, NoValidConnectionsError):
        raise OFAException(f'Cannot remove container {target.name}. Node is down')


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
