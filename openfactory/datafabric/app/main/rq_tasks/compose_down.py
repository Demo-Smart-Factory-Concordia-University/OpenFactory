"""
RQ Task to remove a Docker Compose project
"""
from rq import get_current_job
from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask


def compose_down(compose):
    """ Tears down a Docker Compose project """

    # remove compose project
    compose_name = compose.name
    db.session.delete(compose)
    db.session.commit()

    # clear rq-task
    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())
    rq_task.complete = True
    db.session.commit()
    rq_task.user.send_notification(f'Docker Compose project {compose_name} was removed successfully', "success")
    return True
