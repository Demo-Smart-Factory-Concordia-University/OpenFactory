"""
RQ Task to spin up a new MTConnect Agent
"""
import docker
from rq import get_current_job
from paramiko.ssh_exception import SSHException
from sqlalchemy.exc import PendingRollbackError
from openfactory.exceptions import DockerComposeException
import openfactory.config as config
import openfactory.ofa as ofa
from openfactory.exceptions import OFAException
from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask


def agent_up(agent, container, mtc_file, producer_cpus):
    """ Spins up an MTConnect Agent """
    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())
    current_user = rq_task.user

    # Deploy Agent and container
    try:
        client = docker.DockerClient(base_url=container.node.docker_url)
        client.images.pull(config.MTCONNECT_AGENT_IMAGE)
        db.session.add_all([container, agent])
        db.session.commit()
        container.add_file(mtc_file, '/home/agent/device.xml')
        container.add_file(config.MTCONNECT_AGENT_CFG_FILE, '/home/agent/agent.cfg')
    except (DockerComposeException, PendingRollbackError, SSHException, docker.errors.APIError) as err:
        db.session.rollback()
        rq_task.user.send_notification(f'MTConnect agent {agent.uuid} could not be created. Error was:<br>"{err}"', "danger")
        rq_task.complete = True
        db.session.commit()
        return False

    rq_task.user.send_notification(f'MTConnect agent {agent.uuid} created successfully', "info")

    # Start agent
    try:
        container.start()
    except docker.errors.APIError as err:
        rq_task.user.send_notification(f'MTConnect agent {agent.uuid} could not be started. Error was:<br>"{err}"', "danger")
        rq_task.complete = True
        db.session.commit()
        return False

    rq_task.user.send_notification(f'MTConnect agent {agent.uuid} started successfully', "info")

    # create and start producer
    try:
        ofa.agent.attach(agent.uuid,
                         producer_cpus,
                         user_notification=lambda msg: current_user.send_notification(msg, 'info'))
    except OFAException as err:
        rq_task.user.send_notification(err, "danger")
        rq_task.complete = True
        db.session.commit()
        return False

    rq_task.complete = True
    rq_task.user.send_notification(f'MTConnect agent {agent.uuid} was deployed successfully on {agent.node}', "success")
    return True
