from flask.views import View
from flask import flash
from flask import redirect
from flask import url_for

from openfactory.datafabric.app import db
from openfactory.models.nodes import Node


class NodeRemove(View):

    def dispatch_request(self, node_id):

        query = db.session.query(Node).where(Node.id == node_id)
        node = db.session.execute(query).one()
        node = node[0]

        if node.node_name == 'manager':
            flash('Cannot remove manger node', "danger")
            return redirect(url_for('infra.nodes'))

        if node.containers:
            flash('Cannot remove a node with running containers', "danger")
            return redirect(url_for('infra.nodes'))

        db.session.delete(node)
        db.session.commit()

        flash(f'Removed node {node.node_name}', "success")
        return redirect(url_for('infra.nodes'))
