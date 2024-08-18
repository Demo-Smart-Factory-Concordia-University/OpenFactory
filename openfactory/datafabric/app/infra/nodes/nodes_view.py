"""
DataFabric Swarm Nodes list view
"""
from flask import render_template
from flask.views import View
from flask_login import login_required
from openfactory.docker.docker_access_layer import dal


class NodesList(View):
    """
    Nodes list view
    """

    decorators = [login_required]

    def dispatch_request(self):
        nodes = dal.docker_client.nodes.list()
        node_data = []
        for node in nodes:
            node_info = {
                'ID': node.id,
                'Hostname': node.attrs['Description']['Hostname'],
                'State': node.attrs['Status']['State'],
                'Availability': node.attrs['Spec']['Availability'],
                'Node Type': 'Manager' if 'ManagerStatus' in node.attrs else 'Worker',
                'IP Address': node.attrs['Status']['Addr']
            }
            node_data.append(node_info)
        return render_template("infra/nodes/nodes_list.html", nodes=node_data, title='Nodes')
