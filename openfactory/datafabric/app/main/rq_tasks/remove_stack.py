"""
RQ Task to remove an OpenFactory infrastructure stack
"""
from rq import get_current_job
from openfactory.exceptions import OFAException
from openfactory.models.user_notifications import user_notify
from openfactory.models.infrastack import InfraStack
from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask


def remove_stack(stack_id):
    """
    Remove an OpenFactory infrastructure stack
    """
    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())

    # Setup user notifications
    user_notify.success = lambda msg: rq_task.user.send_notification(msg, "success")
    user_notify.info = lambda msg: rq_task.user.send_notification(msg, "info")
    user_notify.fail = lambda msg: rq_task.user.send_notification(msg, "danger")

    # Object needs to be loaed in worker
    # It can not be passed by DataFabric as it would have no session associated
    stack = db.session.get(InfraStack, stack_id)

    try:
        stack.clear()
        db.session.delete(stack)
        db.session.commit()
    except OFAException as err:
        db.session.rollback()
        user_notify.fail(err)
    finally:
        rq_task.complete = True
        db.session.commit()
