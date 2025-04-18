"""
Routes for DataFabric Infrastructure Blueprint
"""
from flask_login import login_required
from flask import render_template
from openfactory.datafabric.app.infra import infra_blueprint
from openfactory.datafabric.app.infra.nodes.nodes_view import NodesList
from openfactory.datafabric.app.infra.nodes.node_add import NodeAdd
from openfactory.datafabric.app.infra.nodes.node_remove import NodeRemove
from openfactory.datafabric.app.infra.nodes.node_view import NodeView


@infra_blueprint.route('/')
@login_required
def home():
    return render_template('infra/infraBase.html',
                           title='Infrastructure')


infra_blueprint.add_url_rule("/nodes/", view_func=NodesList.as_view("nodes"))
infra_blueprint.add_url_rule("/node/add", view_func=NodeAdd.as_view("node_add"))
infra_blueprint.add_url_rule("/node/remove/<node_id>", view_func=NodeRemove.as_view("node_remove"))
infra_blueprint.add_url_rule("node/view/<node_id>", view_func=NodeView.as_view("node_view"))
