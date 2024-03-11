"""
RQ Task to create a new Docker Compose project
"""
from rq import get_current_job
from paramiko.ssh_exception import SSHException
from sqlalchemy.exc import PendingRollbackError
from openfactory.exceptions import DockerComposeException
from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask


def compose_up(compose):
    """ Spins up Docker Compose Project """
    try:
        db.session.add_all([compose])
        db.session.commit()
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
            rq_task.user.send_notification(f'Docker Compose project {compose.name} could not be deployed. Error was:<br>"{docker_error}"', "danger")
        else:
            rq_task.user.send_notification(f'Docker Compose project {compose.name} was added successfully', "success")
        return True
