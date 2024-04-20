import docker
from typing import List
from typing import Optional
from sqlalchemy import event
from sqlalchemy import select
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import Float
from sqlalchemy.orm import Session
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
import openfactory.config as config
from openfactory.exceptions import OFAException
from .user_notifications import user_notify
from .base import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .agents import Agent
    from .containers import DockerContainer
    from .compose import ComposeProject
    from .infrastack import InfraStack


class Node(Base):
    """
    OpenFactory Node
    """

    __tablename__ = "ofa_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    node_name: Mapped[str] = mapped_column(String(20), unique=True)
    network: Mapped[str] = mapped_column(String(20))
    node_ip: Mapped[str] = mapped_column(String(14), unique=True)
    cpus = mapped_column(Integer())
    memory = mapped_column(Float())
    docker_node_id: Mapped[str] = mapped_column(String(30))
    docker_url: Mapped[str] = mapped_column(String(40),
                                            default='unix://var/run/docker.sock')

    stack_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ofa_infra_stack.id"))
    stack: Mapped[Optional["InfraStack"]] = relationship(back_populates="nodes")

    agents: Mapped[List["Agent"]] = relationship(back_populates="node")
    containers: Mapped[List["DockerContainer"]] = relationship(back_populates="node")
    compose_projects: Mapped[List["ComposeProject"]] = relationship(back_populates="node")

    def __repr__(self):
        return f"{self.node_name.title()} ({self.node_ip})"

    @hybrid_property
    def status(self):
        """ Returns status of swarm node """
        client = docker.DockerClient(base_url=self.manager.docker_url)
        n = client.nodes.get(self.docker_node_id)
        stat = n.attrs['Status']['State']
        client.close()
        return stat

    @hybrid_property
    def manager(self):
        """ Returns swarm manager """
        session = Session.object_session(self)
        query = select(Node).where(Node.node_name == "manager")
        manager = session.execute(query).first()
        return manager[0]


@event.listens_for(Node, 'before_insert')
def node_before_insert(mapper, connection, target):
    """
    Add docker id and create swarm node
    """

    # Check if node is the swarm manager
    if target.node_name == "manager":
        target.docker_url = "ssh://" + config.OPENFACTORY_USER + "@" + target.node_ip
        client = docker.DockerClient(base_url=target.docker_url)
        target.docker_node_id = client.swarm.init(advertise_addr=target.node_ip)
        client.networks.create(target.network,
                               driver='overlay',
                               attachable=True)
        user_notify.success(f"Created network '{target.network}' successfully")
        target.cpus = client.info()['NCPU']
        target.memory = client.info()['MemTotal'] / 1073741824
        client.close()
        user_notify.success("Attached manager node successfully")
        return

    # get manager token
    manager = target.manager
    target.network = manager.network
    client = docker.DockerClient(base_url=manager.docker_url)
    token = client.swarm.attrs['JoinTokens']['Worker']

    # create node on swarm
    target.docker_url = "ssh://" + config.OPENFACTORY_USER + "@" + target.node_ip
    node_client = docker.DockerClient(base_url=target.docker_url)
    node_client.swarm.join([manager.node_ip], join_token=token)

    # get node information
    target.docker_node_id = node_client.info()['Swarm']['NodeID']
    target.cpus = node_client.info()['NCPU']
    target.memory = node_client.info()['MemTotal'] / 1073741824

    client.close()
    node_client.close()
    user_notify.success(f"Attached node '{target.node_name}' successfully")


@event.listens_for(Node, 'before_delete')
def node_before_delete(mapper, connection, target):
    """
    Checks if node can be removed
    """
    if target.containers or target.compose_projects:
        raise OFAException(f"Cannot remove node '{target.node_name}': containers/Docker compose projects are running on it")
    if target.node_name == "manager":
        if len(Session.object_session(target).query(Node).all()) > 1:
            raise OFAException("Manager node not removed as other nodes exist")


@event.listens_for(Node, 'after_delete')
def node_after_delete(mapper, connection, target):
    """
    Remove swarm node when database object is deleted
    """
    client = docker.DockerClient(base_url=target.docker_url)

    # Checks if node is the swarm manager
    if target.node_name == "manager":
        client.swarm.leave(force=True)
        client.close()
        user_notify.success("Removed manager node successfully")
        return

    client.swarm.leave()
    client.close()
    client = docker.APIClient(target.manager.docker_url)
    client.remove_node(target.docker_node_id, force=True)
    client.close()
    user_notify.success(f"Removed node '{target.node_name}' successfully")
