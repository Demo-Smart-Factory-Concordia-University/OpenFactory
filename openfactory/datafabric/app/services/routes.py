"""
Routes for DataFabric Services Blueprint
"""
from flask_login import login_required
from flask import render_template
from . import serv_blueprint
from .agents.agents_view import AgentList
from .agents.agent_add import AgentAdd
from .containers.containers_view import ContainerList


@serv_blueprint.route('/')
@login_required
def home():
    return render_template('services/servicesBase.html',
                           title='Services')


serv_blueprint.add_url_rule("/agents", view_func=AgentList.as_view("agents"))
serv_blueprint.add_url_rule("/agent/add", view_func=AgentAdd.as_view("agent_add"))
serv_blueprint.add_url_rule("/containers", view_func=ContainerList.as_view("containers"))
