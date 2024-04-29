"""
RQ Task to create a new OpenFactory Node
"""
from rq import get_current_job
from docker.errors import APIError
from sqlalchemy.exc import PendingRollbackError
from paramiko.ssh_exception import SSHException
from openfactory.models.user_notifications import user_notify
from openfactory.models.nodes import Node
from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask


def node_up(node_name, node_ip):
    """ Spins up an OpenFactory node """

    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())

    # Setup user notifications
    user_notify.success = lambda msg: rq_task.user.send_notification(msg, "success")
    user_notify.info = lambda msg: rq_task.user.send_notification(msg, "info")
    user_notify.fail = lambda msg: rq_task.user.send_notification(msg, "danger")

    # create new node
    node = Node(
        node_name=node_name,
        node_ip=node_ip
        )
    try:
        db.session.add_all([node])
        db.session.commit()
        docker_error = ''
    except (APIError, PendingRollbackError, SSHException) as err:
        docker_error = err
        db.session.rollback()
    finally:
        rq_task.complete = True
        if docker_error:
            rq_task.user.send_notification(f'Node "{node_name}" could not be setup. Error was:<br>"{docker_error}"', "danger")
        db.session.commit()
    return (not docker_error)
