"""
RQ Task to spin up a new MTConnect Agent
"""
import docker
from rq import get_current_job
from paramiko.ssh_exception import SSHException
from sqlalchemy.exc import PendingRollbackError
from openfactory.exceptions import DockerComposeException
import openfactory.config as config
from openfactory.models.user_notifications import user_notify
from openfactory.exceptions import OFAException
from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask


def agent_up(agent, container, mtc_file, producer_cpus):
    """ Spins up an MTConnect Agent """
    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())

    # Setup user notifications
    user_notify.success = lambda msg: rq_task.user.send_notification(msg, "success")
    user_notify.info = lambda msg: rq_task.user.send_notification(msg, "info")
    user_notify.fail = lambda msg: rq_task.user.send_notification(msg, "danger")

    # Deploy Agent and container
    try:
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

    rq_task.user.send_notification(f'MTConnect agent {agent.uuid} created successfully', "success")

    # Start agent
    try:
        agent.start()
    except docker.errors.APIError as err:
        rq_task.user.send_notification(f'MTConnect agent {agent.uuid} could not be started. Error was:<br>"{err}"', "danger")
        rq_task.complete = True
        db.session.commit()
        return False

    # Create and start producer
    try:
        agent.attach(producer_cpus)
    except OFAException as err:
        rq_task.user.send_notification(err, "danger")
        rq_task.complete = True
        db.session.commit()
        return False

    rq_task.complete = True
    rq_task.user.send_notification(f'MTConnect agent {agent.uuid} deployed successfully on {agent.node}', "success")
    db.session.commit()
    return True
