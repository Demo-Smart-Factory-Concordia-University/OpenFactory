"""
RQ Task to add an OpenFactory infrastructure stack
"""
from docker.errors import APIError
from paramiko.ssh_exception import SSHException
from sqlalchemy.exc import PendingRollbackError
from rq import get_current_job
import openfactory.ofa as ofa
from openfactory.exceptions import OFAConfigurationException
from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask


def add_stack(stack_config_file):
    """
    Add an OpenFactory infrastructure stack
    """
    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())
    current_user = rq_task.user
    try:
        ofa.stack.up(db.session,
                     stack_config_file,
                     user_notification=lambda msg: current_user.send_notification(msg, 'info'))
        rq_task.user.send_notification('Infrastructure stack was added successfully', 'success')
    except (OFAConfigurationException, APIError, SSHException, PendingRollbackError) as err:
        db.session.rollback()
        rq_task.user.send_notification(f'Infrastructure stack could not be setup. Error was:<br>"{err}"', 'danger')
    finally:
        rq_task.complete = True
        db.session.commit()
