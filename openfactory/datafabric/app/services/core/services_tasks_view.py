from dateutil.parser import parse as parse_datetime
from flask.views import View
from flask import render_template
from flask_login import login_required
from datetime import datetime, timezone
from openfactory.docker.docker_access_layer import dal


def calculate_uptime(timestamp):
    """
    Calculate uptime from the given timestamp
    """
    if not timestamp:
        return "Unknown"
    started_at = parse_datetime(timestamp)
    uptime = datetime.now(timezone.utc) - started_at
    minutes = divmod(uptime.total_seconds(), 60)[0]
    if minutes < 60:
        return f"{int(minutes)}m ago"
    hours = divmod(minutes, 60)[0]
    return f"{int(hours)}h {int(minutes % 60)}m ago"


class ServicesTasksListView(View):
    """
    Generic base class for listing all tasks of a list of services
    """

    decorators = [login_required]
    template_name = "services/generic/services_list.html"

    def filter_services(self, services):
        """
        Abstract method to filter specific services
        Must be implemented in derived classes
        """
        raise NotImplementedError("Subclasses must implement filter_services")

    def dispatch_request(self):
        """
        Fetch and process services to generate the list view
        """
        services = dal.docker_client.services.list()
        filtered_services = self.filter_services(services)

        service_list = []

        for service in filtered_services:
            service_info = service.attrs
            service_name = service_info['Spec']['Name']

            # Get tasks associated with the service
            tasks = dal.docker_client.api.tasks(filters={"service": service_name})
            if tasks:
                for task in tasks:
                    node_id = task['NodeID']
                    state = task['Status']['State']
                    timestamp = task["Status"].get("Timestamp", None)
                    uptime = calculate_uptime(timestamp)

                    # Get the node name from the NodeID
                    node_name = dal.docker_client.api.inspect_node(node_id).get('Description', {}).get('Hostname', "Unknown")

                    # Add to the result
                    service_list.append({
                        "name": service_name,
                        "status": f"{state} (since {uptime})",
                        "node": node_name
                    })

        # Render the template with sorted services
        return render_template(self.template_name,
                               services=sorted(service_list, key=lambda x: x["name"]),
                               title=self.service_name)
