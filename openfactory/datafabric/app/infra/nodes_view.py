"""
DataFabric Nodes list view
"""
from sqlalchemy import select
from flask import render_template
from flask.views import View
from openfactory.models.nodes import Node
from openfactory.datafabric.app import db


class NodesList(View):
    """
    Nodes list view
    """

    def dispatch_request(self):
        query = select(Node)
        nodes = db.session.scalars(query)
        return render_template("nodes.html", nodes=nodes, title='Nodes')
