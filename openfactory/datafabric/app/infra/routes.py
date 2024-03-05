"""
Routes for DataFabric Infrastructure Blueprint
"""
from flask_login import login_required
from flask import render_template
from . import bp
from .nodes.nodes_view import NodesList
from .nodes.node_add import NodeAdd
from .nodes.node_remove import NodeRemove
from .compose.compose_listview import ComposeProjecList
from .compose.compose_add import ComposeAdd


@bp.route('/')
@login_required
def home():
    return render_template('infra/infraBase.html',
                           title='Infrastructure')


bp.add_url_rule("/nodes/", view_func=NodesList.as_view("nodes"))
bp.add_url_rule("/node/add", view_func=NodeAdd.as_view("node_add"))
bp.add_url_rule("/node/remove/<int:node_id>", view_func=NodeRemove.as_view("node_remove"))

bp.add_url_rule("/compose/", view_func=ComposeProjecList.as_view("compose_list"))
bp.add_url_rule("/compose/add", view_func=ComposeAdd.as_view("compose_add"))
