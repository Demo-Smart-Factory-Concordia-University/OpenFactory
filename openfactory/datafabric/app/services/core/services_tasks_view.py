from dateutil.parser import parse as parse_datetime
from flask import render_template
from flask_login import login_required
from datetime import datetime, timezone
from openfactory.docker.docker_access_layer import dal
from openfactory.datafabric.app.services.devices.device_services import DeviceServicesList


class ServicesTasksListView(DeviceServicesList):
    """
    Generic base class for listing all tasks of a list of services
    """

    decorators = [login_required]
    template_name = "services/generic/services_task_list.html"

    def filter_services(self, services, service_name):
        """
        Filter services
        """
        return [service for service in services if service.name.endswith(service_name)]

    def calculate_uptime(self, timestamp):
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

    def dispatch_request(self, service_name):
        """
        Fetch and process services to generate the list view
        """
        self.service_name = service_name
        services = dal.docker_client.services.list()
        filtered_services = self.filter_services(services, service_name)

        task_list = []

        for service in filtered_services:
            service_info = service.attrs
            service_name = service_info['Spec']['Name']

            # Get tasks associated with the service
            tasks = dal.docker_client.api.tasks(filters={"service": service_name})
            if tasks:
                for task in tasks:
                    task_id = task["ID"]
                    node_id = task['NodeID']
                    state = task['Status']['State']
                    timestamp = task["Status"].get("Timestamp", None)
                    uptime = self.calculate_uptime(timestamp)

                    # Get the node name from the NodeID
                    node_name = dal.docker_client.api.inspect_node(node_id).get('Description', {}).get('Hostname', "Unknown")

                    # Add to the result
                    task_list.append({
                        "id": task_id,
                        "name": service_name,
                        "status": f"{state} (since {uptime})",
                        "node": node_name,
                        "timestamp": timestamp
                    })

        # Sort the list by timestamp, most recent first
        task_list = sorted(task_list, key=lambda x: parse_datetime(x["timestamp"]) if x["timestamp"] else datetime.min, reverse=True)

        # Render the template with sorted services
        return render_template(self.template_name,
                               service_tasks=sorted(task_list, key=lambda x: x["name"]),
                               data=self.fetch_data(service_name.upper()),
                               title=self.service_name)
