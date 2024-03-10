"""
RQ Task to remove an OpenFactory Node
"""
from rq import get_current_job
from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask


def node_down(node):
    """ Tears down an OpenFactory node """

    # remove node
    db.session.delete(node)
    db.session.commit()

    # clear rq-task
    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())
    rq_task.complete = True
    db.session.commit()
    return True
