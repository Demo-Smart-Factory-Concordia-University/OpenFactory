"""
RQ Task to remove an MTConnect Agent
"""
from rq import get_current_job
from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask


def agent_down(agent):
    """ Tears down an MTConnect Agent """

    # remove agent
    agent_uuid = agent.uuid
    db.session.delete(agent)
    db.session.commit()

    # clear rq-task
    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())
    rq_task.complete = True
    db.session.commit()
    rq_task.user.send_notification(f'MTConnect Agent {agent_uuid} was removed successfully', "success")
    return True
