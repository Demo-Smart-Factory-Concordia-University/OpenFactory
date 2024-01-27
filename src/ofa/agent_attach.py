import docker
from sqlalchemy import update
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.models.agents import Agent


def agent_attach(agent_uuid, db_engine):
    """ Attach a Kafka producer to an MTConnect agent """

    session = Session(db_engine)
    query = select(Agent).where(Agent.uuid == agent_uuid)
    agent = session.execute(query).one()[0]

    client = docker.from_env()
    client.images.pull("rwuthric/kafka-mtc-producer")

    producer_url = agent_uuid.lower().replace("-agent", "-producer")

    kafka_producer = client.containers.create('rwuthric/kafka-mtc-producer',
                                              name=producer_url,
                                              detach=True,
                                              environment=["KAFKA_BROKER=broker:29092",
                                                           f"KAFKA_PRODUCER_UUID={agent.uuid.upper().replace('-AGENT', '-PRODUCER')}",
                                                           f"MTC_AGENT={agent.agent_url}:{agent.agent_port}",
                                                           f"MTC_AGENT_UUID={agent_uuid}"],
                                              network='factory-net')

    kafka_producer.start()

    query = update(Agent).where(Agent.uuid == agent_uuid).values(producer_url=producer_url)
    session.execute(query)
    session.commit()
