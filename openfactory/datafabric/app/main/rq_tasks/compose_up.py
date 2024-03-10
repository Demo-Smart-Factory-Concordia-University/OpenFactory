"""
RQ Task to create a new Docker Compose project
"""
from rq import get_current_job
# from openfactory.models.compose import ComposeProject
from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask


def compose_up(compose):
    """ Spins up Docker Compose Project """
    
    db.session.add_all([compose])
    db.session.commit()

    # clear rq-task
    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())
    rq_task.complete = True
    db.session.commit()
    rq_task.user.send_notification(f'Docker Compose project {compose.name} was added successfully', "success")
    return True
