"""
DataFabric Swarm Node detail view
"""
from datetime import datetime, timezone
from flask import render_template
from flask.views import View
from flask_login import login_required
from openfactory.docker.docker_access_layer import dal


class NodeView(View):
    """
    Node detail view
    """

    decorators = [login_required]

    def dispatch_request(self, node_id):
        services = dal.docker_client.services.list()
        node = dal.docker_client.nodes.get(node_id)
        node_info = {
                        'ID': node.id,
                        'Hostname': node.attrs['Description']['Hostname'],
                        'IP': node.attrs['Status']['Addr']
        }
        services_info = []
        for service in services:
            tasks = dal.docker_client.api.tasks(filters={"service": service.name})
            for task in tasks:
                if task['NodeID'] == node_id and task['Status']['State'] == 'running':
                    ports = service.attrs.get('Endpoint', {}).get('Ports', [])
                    public_ports = ', '.join([str(port['PublishedPort']) for port in ports if 'PublishedPort' in port])
                    started_at_str = task['Status']['Timestamp']
                    trimmed_timestamp = started_at_str[:26] + 'Z'
                    started_at = datetime.strptime(trimmed_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                    time_running = datetime.now(timezone.utc) - started_at
                    hours, remainder = divmod(time_running.total_seconds(), 3600)
                    minutes, _ = divmod(remainder, 60)
                    running_for = f"{int(hours)}h {int(minutes)}m ago" if hours else f"{int(minutes)}m ago"
                    service_info = {
                        'Service': service.name,
                        'Running_for': running_for,
                        'Ports': public_ports
                    }
                    services_info.append(service_info)

        return render_template("infra/nodes/node_view.html", node=node_info, services=services_info, title=f"Node {node.attrs['Description']['Hostname']}")
