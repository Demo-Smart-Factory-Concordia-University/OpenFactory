from flask.views import View
from flask import flash
from flask import redirect
from flask import url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from openfactory.models.nodes import Node
import openfactory.config as config


class NodeRemove(View):

    def dispatch_request(self, node_id):

        db = create_engine(config.SQL_ALCHEMY_CONN)
        session = Session(db)
        query = session.query(Node).where(Node.id == node_id)
        node = session.execute(query).one()
        node = node[0]

        if node.node_name == 'manager':
            flash('Cannot remove manger node', "danger")
            return redirect(url_for('infra.nodes'))

        if node.containers:
            flash('Cannot remove a node with running containers', "danger")
            return redirect(url_for('infra.nodes'))

        session.delete(node)
        session.commit()
        session.close()

        flash(f'Removed node {node.node_name}', "success")
        return redirect(url_for('infra.nodes'))
