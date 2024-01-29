from sqlalchemy import select
from sqlalchemy.orm import Session
from src.models.agents import Agent


def ls(db_engine):
    """ List MTConnect agents defined in OpenFactory """
    session = Session(db_engine)
    agents = select(Agent)
    print('UUID            URL             PORT     STATUS         ATTACHED')
    for agent in session.scalars(agents):
        print(f'{agent.uuid:15} {agent.agent_url:15} {agent.agent_port:<8d} {agent.status}        {agent.attached}')
