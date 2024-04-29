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

    # setup user notifications
    user_notify.success = lambda msg: rq_task.user.send_notification(msg, "success")
    user_notify.info = lambda msg: rq_task.user.send_notification(msg, "info")
    user_notify.fail = lambda msg: rq_task.user.send_notification(msg, "danger")

    try:
        create_infrastack(db.session, stack_config_file)
    except (OFAConfigurationException, APIError, SSHException, PendingRollbackError) as err:
        db.session.rollback()
        rq_task.user.send_notification(f'Infrastructure stack could not be setup. Error was:<br>"{err}"', 'danger')
    finally:
        rq_task.complete = True
        db.session.commit()
