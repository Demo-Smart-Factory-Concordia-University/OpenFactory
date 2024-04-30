"""
RQ Task to spin up a new MTConnect Agent
"""
import docker
from rq import get_current_job
from paramiko.ssh_exception import SSHException
from sqlalchemy.exc import PendingRollbackError
from openfactory.exceptions import DockerComposeException
from openfactory.models.user_notifications import user_notify
from openfactory.exceptions import OFAException
from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask


def agent_up(agent, adapter_ip, adapter_port, mtc_file, agent_cpus, producer_cpus):
    """ Spins up an MTConnect Agent """
    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())
    user_notify.user = rq_task.user

    # Deploy Agent and container
    try:
        db.session.add(agent)
        db.session.commit()
        agent.create_container(adapter_ip, adapter_port, mtc_file, agent_cpus)
    except (DockerComposeException, PendingRollbackError, SSHException, docker.errors.APIError) as err:
        db.session.rollback()
        user_notify.fail(f'MTConnect agent {agent.uuid} could not be created. Error was:<br>"{err}"')
        rq_task.complete = True
        db.session.commit()
        return False

    # Start agent
    try:
        agent.start()
    except docker.errors.APIError as err:
        user_notify.fail(f'MTConnect agent {agent.uuid} could not be started. Error was:<br>"{err}"')
        rq_task.complete = True
        db.session.commit()
        return False

    # Create and start producer
    try:
        agent.attach(producer_cpus)
    except OFAException as err:
        user_notify.fail(err)
        rq_task.complete = True
        db.session.commit()
        return False

    rq_task.complete = True
    user_notify.success(f'MTConnect agent {agent.uuid} deployed successfully on {agent.node}')
    db.session.commit()
    user_notify.user = None
    return True
