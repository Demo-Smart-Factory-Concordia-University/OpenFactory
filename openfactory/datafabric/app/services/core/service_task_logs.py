import docker
from flask import render_template
from flask.views import View
from flask_login import login_required
from openfactory.docker.docker_access_layer import dal
import openfactory.config as config


class ServiceTaskLogs(View):
    """
    View for logs of a service task
    """

    decorators = [login_required]

    def dispatch_request(self, task_id):
        """ retrieve logs of a task on the Swarm node where the task is deployed """
        task = dal.docker_client.api.inspect_task(task_id)
        node = dal.docker_client.api.inspect_node(task['NodeID'])
        node_client = docker.DockerClient(base_url=f"ssh://{config.OPENFACTORY_USER}@{node['Status']['Addr']}")
        logs = node_client.api.logs(task['Status']['ContainerStatus']['ContainerID'], tail=25)
        service = dal.docker_client.api.inspect_service(task['ServiceID'])

        return render_template('services/generic/task_logs.html',
                               logs=logs.decode() + '<br>',
                               title=service['Spec']['Name'])
