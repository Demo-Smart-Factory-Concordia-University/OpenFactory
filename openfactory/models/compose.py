import os
from python_on_whales import DockerClient
from sqlalchemy import event
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from .base import Base
from .configurations import get_configuration
from openfactory.utils import docker_compose_up
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .nodes import Node


class ComposeProject(Base):
    """
    Docker Compose project
    """

    __tablename__ = 'compose_projects'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)
    description: Mapped[str] = mapped_column(String(80))
    yaml_config: Mapped[str] = mapped_column(Text)
    node_id = mapped_column(ForeignKey("ofa_nodes.id"))
    node: Mapped["Node"] = relationship(back_populates="compose_projects")

    def __repr__(self):
        return self.name


@event.listens_for(ComposeProject, 'after_insert')
def composeProject_after_insert(mapper, connection, target):
    """
    Create Docker Compose project after a database object is inserted
    """
    datastore_system = get_configuration('datastore_system')
    if datastore_system is None:
        raise Exception("Cannot create Docker Compose projects. Administrator needs first to configure the 'datastore_system' variable")
        return
    compose_file = os.path.join(datastore_system, target.name + '.yml')
    f = open(compose_file, 'w')
    f.write(target.yaml_config)
    f.close()
    docker_compose_up(host=target.node.docker_url,
                      compose_file=compose_file,
                      compose_project_name=target.name.lower())
    os.remove(compose_file)


@event.listens_for(ComposeProject, 'after_delete')
def composeProject_after_delete(mapper, connection, target):
    """
    Remove Docker Compose project when database object is deleted
    """

    datastore_system = get_configuration('datastore_system')
    if datastore_system is None:
        raise Exception("Cannot remove Docker Compose projects. Administrator needs first to configure the 'datastore_system' variable")
        return
    compose_file = os.path.join(datastore_system, target.name + '.yml')
    f = open(compose_file, 'w')
    f.write(target.yaml_config)
    f.close()
    docker = DockerClient(host=target.node.docker_url,
                          compose_files=[compose_file],
                          compose_project_name=target.name.lower())
    docker.compose.down()
    os.remove(compose_file)
