from flask.views import View
from flask import render_template
from flask_login import login_required
from openfactory.docker.docker_access_layer import dal


class ServicesListView(View):
    """
    Generic base class for listing services
    """

    decorators = [login_required]
    template_name = "services/generic/services_list.html"

    def filter_services(self):
        """
        Abstract method to filter specific services
        Must be implemented in derived classes
        """
        raise NotImplementedError("Subclasses must implement filter_services")

    def fetch_service_list(self):
        """
        Returns the sorted (by name) service list
        """
        service_list = []

        for service in self.filter_services():

            # Discard services not deployed as Docker Services
            if service == '':
                continue

            # Fetch tasks associated with the service
            tasks = dal.docker_client.api.tasks(filters={"service": service})

            # Determine the service status based on task states
            is_online = any(task["Status"]["State"] == "running" for task in tasks)
            status = "online" if is_online else "offline"

            service_list.append({
                "name": service,
                "status": status
            })

        return sorted(service_list, key=lambda x: x["name"])

    def dispatch_request(self):
        """
        Fetch and process services to generate the list view
        """
        # Render the template with sorted services
        return render_template(self.template_name,
                               services=self.fetch_service_list(),
                               title=self.service_name)
