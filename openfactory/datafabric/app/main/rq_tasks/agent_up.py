"""
RQ Task to spin up a new MTConnect Agent
"""
import docker
from rq import get_current_job
from pyksql.ksql import KSQL
from httpx import HTTPError
from paramiko.ssh_exception import SSHException
from sqlalchemy.exc import PendingRollbackError
from openfactory.exceptions import DockerComposeException
import openfactory.config as config
from openfactory.models.containers import DockerContainer, EnvVar
from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask


def agent_up(agent, container, mtc_file):
    """ Spins up an MTConnect Agent """
    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())

    # Deploy Agent and container
    try:
        client = docker.DockerClient(base_url=container.node.docker_url)
        client.images.pull(config.MTCONNECT_AGENT_IMAGE)
        db.session.add_all([container, agent])
        db.session.commit()
        container.add_file(mtc_file, '/home/agent/device.xml')
        container.add_file(config.MTCONNECT_AGENT_CFG_FILE, '/home/agent/agent.cfg')
    except (DockerComposeException, PendingRollbackError, SSHException) as err:
        db.session.rollback()
        rq_task.user.send_notification(f'MTConnect agent {agent.uuid} could not be created. Error was:<br>"{err}"', "danger")
        rq_task.complete = True
        db.session.commit()
        return False

    rq_task.user.send_notification(f'MTConnect agent {agent.uuid} created successfully', "success")

    # Start agent
    container.start()
    rq_task.user.send_notification(f'MTConnect agent {agent.uuid} started successfully', "success")

    # Create ksqlDB table for device handeld by the agent
    ksql = KSQL(config.KSQLDB)
    try:
        ksql._statement_query(f"""CREATE TABLE IF NOT EXISTS {agent.device_uuid.replace('-', '_')} AS
                                      SELECT id,
                                             LATEST_BY_OFFSET(value) AS value
                                      FROM devices_stream
                                      WHERE device_uuid = '{agent.device_uuid}'
                                      GROUP BY id;""")
    except HTTPError:
        rq_task.user.send_notification(f"Could not connect to KSQLdb {config.KSQLDB}", "danger")
        rq_task.complete = True
        db.session.commit()
        return False

    # create producer
    producer = DockerContainer(
        node_id=agent.node.id,
        node=agent.node,
        image=config.MTCONNECT_PRODUCER_IMAGE,
        name=agent.uuid.lower().replace("-agent", "-producer"),
        environment=[
            EnvVar(variable='KAFKA_BROKER', value=config.KAFKA_BROKER),
            EnvVar(variable='KAFKA_PRODUCER_UUID', value=agent.uuid.upper().replace('-AGENT', '-PRODUCER')),
            EnvVar(variable='MTC_AGENT', value=f"{agent.agent_url}:{agent.agent_port}"),
            EnvVar(variable='MTC_AGENT_UUID', value='agent_uuid')
        ]
    )
    agent.producer_container = producer
    try:
        client.images.pull(config.MTCONNECT_PRODUCER_IMAGE)
        db.session.add_all([producer])
        db.session.commit()
    except (DockerComposeException, PendingRollbackError, SSHException) as err:
        db.session.rollback()
        rq_task.user.send_notification(f'Producer for agent {agent.uuid} could not be created. Error was:<br>"{err}"', "danger")
        rq_task.complete = True
        db.session.commit()
        return False

    rq_task.user.send_notification(f'Producer for agent {agent.uuid} created successfully', "success")

    # Start prodcuer
    producer.start()
    rq_task.user.send_notification(f'Producer for agent {agent.uuid} started successfully', "success")

    client.close()
    rq_task.complete = True
    db.session.commit()
    rq_task.user.send_notification(f'MTConnect agent {agent.uuid} was deployed successfully on {agent.node}', "success")
    return True
