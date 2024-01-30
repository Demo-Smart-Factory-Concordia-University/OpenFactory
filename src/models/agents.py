import docker
from sqlalchemy import Boolean
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class Base(DeclarativeBase):
    pass


class Agent(Base):
    __tablename__ = "mtc_agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(30))
    external = mapped_column(Boolean, default=False)
    agent_port = mapped_column(Integer())
    agent_url: Mapped[str] = mapped_column(String(30))
    producer_url: Mapped[str] = mapped_column(String(30))

    @hybrid_property
    def container(self):
        """ Container of agent """
        if self.external:
            return ""
        return self.uuid.lower()

    @hybrid_property
    def status(self):
        """ Status of agent """
        if self.external:
            return "TO BE DONE"
        client = docker.DockerClient(base_url="ssh://" + self.agent_url)
        container = client.containers.get(self.uuid.lower())
        return container.attrs['State']['Status']

    @hybrid_property
    def attached(self):
        """ kafka producer attached or not """
        if self.producer_url:
            return "yes"
        else:
            return "no"

    def __repr__(self) -> str:
        return f"Agent (id={self.id!r}, uuid={self.uuid!r}, agent_url={self.agent_url!r})"
