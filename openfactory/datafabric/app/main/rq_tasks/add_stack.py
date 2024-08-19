"""
RQ Task to add an OpenFactory infrastructure stack
"""
from docker.errors import APIError
from paramiko.ssh_exception import SSHException
from sqlalchemy.exc import PendingRollbackError
from rq import get_current_job
from openfactory.models.user_notifications import user_notify
from openfactory.factories import create_infrastack
from openfactory.exceptions import OFAConfigurationException
from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask


def add_stack(stack_config_file):
    """
    Add an OpenFactory infrastructure stack
    """
    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())
    user_notify.user = rq_task.user

    try:
        create_infrastack(stack_config_file)
    except (OFAConfigurationException, APIError, SSHException, PendingRollbackError) as err:
        db.session.rollback()
        user_notify.fail(f'Infrastructure stack could not be setup. Error was:<br>"{err}"')
    finally:
        rq_task.complete = True
        db.session.commit()
        user_notify.user = None
