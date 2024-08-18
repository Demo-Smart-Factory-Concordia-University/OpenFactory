"""
RQ Task to create a new OpenFactory Node
"""
import docker
import openfactory.config as config
from rq import get_current_job
from docker.errors import APIError
from openfactory.models.user_notifications import user_notify
from openfactory.datafabric.app import db
from openfactory.docker.docker_access_layer import dal
from openfactory.datafabric.app.main.models.tasks import RQTask


def node_up(node_name, node_ip):
    """ Spins up an OpenFactory node """

    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())
    user_notify.user = rq_task.user

    # create new node
    try:
        docker_url = f"ssh://{config.OPENFACTORY_USER}@{node_ip}"
        node_client = docker.DockerClient(base_url=docker_url)
        node_client.swarm.join([dal.ip], join_token=dal.worker_token)
        docker_error = ''
    except (APIError) as err:
        docker_error = err
    finally:
        rq_task.complete = True
        if docker_error:
            user_notify.fail(f'Node "{node_name}" could not be setup. Error was:<br>"{docker_error}"')
        db.session.commit()
        user_notify.user = None
