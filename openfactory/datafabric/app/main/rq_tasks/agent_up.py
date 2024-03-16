"""
RQ Task to spin up a new MTConnect Agent
"""
import docker
from rq import get_current_job
from paramiko.ssh_exception import SSHException
from sqlalchemy.exc import PendingRollbackError
from openfactory.exceptions import DockerComposeException
import openfactory.config as config
from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask


def agent_up(agent, container, mtc_file):
    """ Spins up an MTConnect Agent """
    try:
        client = docker.DockerClient(base_url=container.node.docker_url)
        client.images.pull(config.MTCONNECT_AGENT_IMAGE)
        db.session.add_all([container, agent])
        db.session.commit()
        container.add_file(mtc_file, '/home/agent/device.xml')
        container.add_file(config.MTCONNECT_AGENT_CFG_FILE, '/home/agent/agent.cfg')
        docker_error = ''
    except (DockerComposeException, PendingRollbackError, SSHException) as err:
        docker_error = err
        db.session.rollback()
    finally:
        job = get_current_job()
        rq_task = db.session.get(RQTask, job.get_id())
        rq_task.complete = True
        db.session.commit()
        if docker_error:
            rq_task.user.send_notification(f'MTConnect agent {agent.uuid} could not be deployed. Error was:<br>"{docker_error}"', "danger")
        else:
            rq_task.user.send_notification(f'MTConnect agent {agent.uuid} was deployed successfully', "success")
        return True
