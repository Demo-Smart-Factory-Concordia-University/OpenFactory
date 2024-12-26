from flask import render_template
from flask.views import View
from flask_login import login_required
from openfactory.docker.docker_access_layer import dal


class ServiceTaskLogs(View):
    """
    View for logs of a service task
    """

    decorators = [login_required]

    def dispatch_request(self, task_id):
        task = dal.docker_client.api.inspect_task(task_id)
        service = dal.docker_client.api.inspect_service(task['ServiceID'])
        service_name = service['Spec']['Name']

        container_id = task['Status']['ContainerStatus']['ContainerID']
        logs = dal.docker_client.api.logs(container_id, stdout=True, stderr=True, tail=25)

        return render_template('services/generic/task_logs.html',
                               logs=logs.decode() + '<br>',
                               title=service_name)
