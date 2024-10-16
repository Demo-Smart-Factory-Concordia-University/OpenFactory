"""
Routes for DataFabric Infrastructure Blueprint
"""
from flask_login import login_required
from flask import render_template
from . import infra_blueprint
from .nodes.nodes_view import NodesList
from .nodes.node_add import NodeAdd
from .nodes.node_remove import NodeRemove
from .nodes.node_view import NodeView
from .compose.compose_listview import ComposeProjecList
from .compose.compose_add import ComposeAdd
from .compose.compose_remove import ComposeRemove


@infra_blueprint.route('/')
@login_required
def home():
    return render_template('infra/infraBase.html',
                           title='Infrastructure')


infra_blueprint.add_url_rule("/nodes/", view_func=NodesList.as_view("nodes"))
infra_blueprint.add_url_rule("/node/add", view_func=NodeAdd.as_view("node_add"))
infra_blueprint.add_url_rule("/node/remove/<node_id>", view_func=NodeRemove.as_view("node_remove"))
infra_blueprint.add_url_rule("node/view/<node_id>", view_func=NodeView.as_view("node_view"))

infra_blueprint.add_url_rule("/compose/", view_func=ComposeProjecList.as_view("compose_list"))
infra_blueprint.add_url_rule("/compose/add", view_func=ComposeAdd.as_view("compose_add"))
infra_blueprint.add_url_rule("/compose/remove/<int:compose_id>", view_func=ComposeRemove.as_view("compose_remove"))
