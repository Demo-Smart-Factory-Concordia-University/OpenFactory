from typing import List
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from .base import Base


class DockerContainer(Base):
    """ Docker container """

    __tablename__ = "docker_container"

    id: Mapped[int] = mapped_column(primary_key=True)
    image: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(20))
    network: Mapped[str] = mapped_column(String(20))
    command: Mapped[str] = mapped_column(String(40), default='')
    environment: Mapped[List["EnvVar"]] = relationship(back_populates="container",
                                                       cascade="all, delete-orphan")
    ports: Mapped[List["Port"]] = relationship(back_populates="container",
                                               cascade="all, delete-orphan")

    def __repr__(self):
        return f"Container (id={self.id} name={self.name})"

    def create(self, docker_client):
        """ Create Docker container """

        ports_dict = {}
        for p in self.ports:
            ports_dict[p.container_port] = p.host_port
        env = []
        for var in self.environment:
            env.append(f"{var.variable}={var.value}")

        return docker_client.containers.create(self.image,
                                               name=self.name,
                                               detach=True,
                                               environment=env,
                                               ports=ports_dict,
                                               command=self.command,
                                               network=self.network)


class EnvVar(Base):
    """ Environment variables for a Docker container """

    __tablename__ = "container_envVars"

    id: Mapped[int] = mapped_column(primary_key=True)
    variable: Mapped[str] = mapped_column(String(20))
    value: Mapped[str] = mapped_column(String(20))
    container_id = mapped_column(ForeignKey("docker_container.id"))
    container: Mapped["DockerContainer"] = relationship(back_populates="environment")

    def __repr__(self):
        return f"Environment variable (id={self.id} variable={self.variable} value={self.value})"


class Port(Base):
    """ Port for a Docker container """

    __tablename__ = "container_ports"

    id: Mapped[int] = mapped_column(primary_key=True)
    container_port: Mapped[str] = mapped_column(String(20))
    host_port: Mapped[int] = mapped_column(Integer())
    container_id = mapped_column(ForeignKey("docker_container.id"))
    container: Mapped["DockerContainer"] = relationship(back_populates="ports")

    def __repr__(self):
        return f"Port (id={self.id} container_port={self.host_port} value={self.host_port})"
