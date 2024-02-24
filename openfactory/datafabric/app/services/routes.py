"""
Routes for DataFabric Services Blueprint
"""
from flask_login import login_required
from flask import render_template
from . import bp
from .agents.agents_view import AgentList
from .containers.containers_view import ContainerList


@bp.route('/')
@login_required
def home():
    return render_template('servicesBase.html',
                           title='Home')


bp.add_url_rule("/agents", view_func=AgentList.as_view("agents"))
bp.add_url_rule("/containers", view_func=ContainerList.as_view("containers"))
