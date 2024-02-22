"""
Routes for DataFabric Infrastructure Blueprint
"""
from . import bp
from .nodes_view import NodesList


bp.add_url_rule("/nodes/", view_func=NodesList.as_view("nodes"))
