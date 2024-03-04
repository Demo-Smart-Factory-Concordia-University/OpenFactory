"""
Routes for DataFabric Infrastructure Blueprint
"""
from flask_login import login_required
from flask import render_template
from . import bp
from .nodes.nodes_view import NodesList
from .nodes.node_add import NodeAdd
from .nodes.node_remove import NodeRemove


@bp.route('/')
@login_required
def home():
    return render_template('infra/infraBase.html',
                           title='Infrastructure')


bp.add_url_rule("/nodes/", view_func=NodesList.as_view("nodes"))
bp.add_url_rule("/node/add", view_func=NodeAdd.as_view("node_add"))
bp.add_url_rule("/node/remove/<int:node_id>", view_func=NodeRemove.as_view("node_remove"))
