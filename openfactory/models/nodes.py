import docker
from typing import List
from sqlalchemy import event
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy import String
from sqlalchemy.orm import Session
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
import openfactory.config as config
from .base import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .agent import Agent


class Node(Base):
    """
    OpenFactory Node
    """

    __tablename__ = "ofa_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    node_name: Mapped[str] = mapped_column(String(20), unique=True)
    network: Mapped[str] = mapped_column(String(20))
    node_ip: Mapped[str] = mapped_column(String(14), unique=True)
    docker_node_id: Mapped[str] = mapped_column(String(30))
    docker_url: Mapped[str] = mapped_column(String(40),
                                            default='unix://var/run/docker.sock')
    agents: Mapped[List["Agent"]] = relationship(back_populates="node")

    def __repr__(self):
        return f"{self.node_name} ({self.node_ip})"

    @hybrid_property
    def status(self):
        """ Returns status of swarm node """
        client = docker.DockerClient(base_url="ssh://openfactory@127.0.0.1")
        n = client.nodes.get(self.docker_node_id)
        stat = n.attrs['Status']['State']
        client.close()
        return stat

    @hybrid_property
    def manager(self):
        """ Returns swarm manager """
        db_engine = create_engine(config.SQL_ALCHEMY_CONN)
        session = Session(db_engine)
        query = select(Node).where(Node.node_name == "manager")
        manager = session.execute(query).first()
        session.close()
        return manager[0]


@event.listens_for(Node, 'before_insert')
def add_docker_node_id(mapper, connection, target):
    """
    Finds and adds docker id
    """

    # Checks if node is the swarm manager
    if target.node_name == "manager":
        target.docker_url = "ssh://" + config.OPENFACTORY_USER + "@" + target.node_ip
        client = docker.DockerClient(base_url=target.docker_url)
        target.docker_node_id = client.swarm.init(advertise_addr=target.node_ip)
        client.networks.create(target.network,
                               driver='overlay',
                               attachable=True)
        client.close()
        return

    # gets manager token
    manager = target.manager
    target.network = manager.network
    client = docker.DockerClient(base_url=manager.docker_url)
    token = client.swarm.attrs['JoinTokens']['Worker']

    # create node on swarm
    target.docker_url = "ssh://" + config.OPENFACTORY_USER + "@" + target.node_ip
    node_client = docker.DockerClient(base_url=target.docker_url)
    node_client.swarm.join([manager.node_ip], join_token=token)

    # finds and adds docker id of node
    for n in client.nodes.list():
        if n.attrs['Status']['Addr'] == target.node_ip:
            target.docker_node_id = n.attrs['ID']
    client.close()
    node_client.close()
