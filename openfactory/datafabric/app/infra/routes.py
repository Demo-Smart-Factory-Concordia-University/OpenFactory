"""
Routes for DataFabric Infrastructure Blueprint
"""
from flask_login import login_required
from flask import render_template
from . import bp
from .nodes_view import NodesList


@bp.route('/')
@login_required
def home():
    return render_template('infra/infraBase.html',
                           title='Infrastructure')


bp.add_url_rule("/nodes/", view_func=NodesList.as_view("nodes"))
