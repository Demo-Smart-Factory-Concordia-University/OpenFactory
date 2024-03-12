"""
RQ Task to remove an OpenFactory infrastructure stack
"""
from rq import get_current_job
from openfactory.core import remove_infra_stack
from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask


def remove_stack(stack):
    """
    Remove an OpenFactory infrastructure stack
    """
    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())
    current_user = rq_task.user
    remove_infra_stack(db.session, stack.id,
                       user_notification_success=lambda msg: current_user.send_notification(msg, 'success'),
                       user_notification_fail=lambda msg: current_user.send_notification(msg, 'danger'))
    rq_task.complete = True
    db.session.commit()
