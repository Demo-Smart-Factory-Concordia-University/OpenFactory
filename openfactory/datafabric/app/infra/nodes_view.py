"""
DataFabric Nodes list view
"""
from sqlalchemy import select
from flask import render_template
from flask.views import View
from flask_login import login_required
from openfactory.models.nodes import Node
from openfactory.datafabric.app import db


class NodesList(View):
    """
    Nodes list view
    """

    decorators = [login_required]

    def dispatch_request(self):
        query = select(Node)
        nodes = db.session.scalars(query)
        return render_template("nodes.html", nodes=nodes, title='Nodes')
