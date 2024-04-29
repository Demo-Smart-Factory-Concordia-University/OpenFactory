from flask.views import View
from flask import flash
from flask import redirect
from flask import url_for
from flask_login import login_required, current_user

from openfactory.datafabric.app import db
from openfactory.models.nodes import Node


class NodeRemove(View):

    decorators = [login_required]

    def dispatch_request(self, node_id):

        node = db.session.get(Node, node_id)

        if node.node_name == 'manager':
            flash('Cannot remove manger node', "danger")
            return redirect(url_for('infra.nodes'))

        if node.containers:
            flash('Cannot remove a node with running containers', "danger")
            return redirect(url_for('infra.nodes'))

        if node.compose_projects:
            flash('Cannot remove a node with running compose projects', "danger")
            return redirect(url_for('infra.nodes'))

        current_user.submit_RQ_task('node_down',
                                    'Removing node ' + node.node_name + '...',
                                    node)

        return redirect(url_for('infra.home'))
