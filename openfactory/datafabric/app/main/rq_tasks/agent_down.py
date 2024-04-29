"""
RQ Task to remove an MTConnect Agent
"""
from rq import get_current_job
from openfactory.models.user_notifications import user_notify
from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask


def agent_down(agent):
    """ Tears down an MTConnect Agent """
    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())

    # setup user notifications
    user_notify.success = lambda msg: rq_task.user.send_notification(msg, "success")
    user_notify.info = lambda msg: rq_task.user.send_notification(msg, "info")
    user_notify.fail = lambda msg: rq_task.user.send_notification(msg, "danger")

    # remove agent
    db.session.delete(agent)
    db.session.commit()

    # clear rq-task
    rq_task.complete = True
    db.session.commit()
    return True
