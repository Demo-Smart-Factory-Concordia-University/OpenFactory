import docker
from sqlalchemy import String
from sqlalchemy import Boolean
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
    agent_url: Mapped[str] = mapped_column(String(30))
    producer_url: Mapped[str] = mapped_column(String(30))

    @hybrid_property
    def status(self):
        """ status of agent """
        if self.external:
            return "TO BE DONE"
        client = docker.from_env()
        container = client.containers.get(self.agent_url)
        return container.attrs['State']['Status']

    def __repr__(self) -> str:
        return f"Agent (id={self.id!r}, uuid={self.uuid!r}, agent_url={self.agent_url!r})"
