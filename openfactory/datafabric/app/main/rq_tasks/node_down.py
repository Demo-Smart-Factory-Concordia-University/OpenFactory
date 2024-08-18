"""
RQ Task to remove an OpenFactory Node
"""
import docker
import openfactory.config as config
from rq import get_current_job
from docker.errors import APIError, NotFound
from openfactory.models.user_notifications import user_notify
from openfactory.datafabric.app import db
from openfactory.docker.docker_access_layer import dal
from openfactory.datafabric.app.main.models.tasks import RQTask


def node_down(node_id):
    """ Tears down an OpenFactory node """

    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())
    user_notify.user = rq_task.user

    client = dal.docker_client
    node = client.nodes.get(node_id)
    node_name = node.attrs['Description']['Hostname']

    # remove node
    try:
        # leave swarm on worker node
        node_client = docker.DockerClient(base_url=f"ssh://{config.OPENFACTORY_USER}@{node.attrs['Status']['Addr']}")
        node_client.swarm.leave()
        # remove node on OpenFactory Manger Node
        client.api.remove_node(node_id, force=True)
        docker_error = ''
    except (APIError, NotFound) as err:
        docker_error = err
    finally:
        rq_task.complete = True
        db.session.commit()
        if docker_error:
            user_notify.fail(f'Node "{node_name}" could not be removed. Error was:<br>"{docker_error}"')
        user_notify.user = None
