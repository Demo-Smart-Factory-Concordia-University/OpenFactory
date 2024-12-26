"""
Routes for DataFabric Services Blueprint
"""
from flask_login import login_required
from flask import render_template
from . import serv_blueprint
from .agents.agents_view import AgentList
from .agents.agent_add import AgentAdd
from .agents.agent_remove import AgentRemove
from .agents.agents_load import AgentStackLoad
from .supervisors.supervisors_view import SupervisorsList
from .producers.producers_view import ProducersList
from .influxdb_connectors.influxdb_connectors_view import InfluxdbConnectorsList
from .core.services_tasks_view import ServicesTasksListView


@serv_blueprint.route('/')
@login_required
def home():
    return render_template('services/servicesBase.html',
                           title='Services')


serv_blueprint.add_url_rule("/agents", view_func=AgentList.as_view("agents"))
serv_blueprint.add_url_rule("/agent/add", view_func=AgentAdd.as_view("agent_add"))
serv_blueprint.add_url_rule("/agent/remove/<int:agent_id>", view_func=AgentRemove.as_view("agent_remove"))
serv_blueprint.add_url_rule("/agent/load_stack", view_func=AgentStackLoad.as_view("agent_load_stack"))

serv_blueprint.add_url_rule("/supervisors", view_func=SupervisorsList.as_view("supervisors"))
serv_blueprint.add_url_rule("/producers", view_func=ProducersList.as_view("producers"))
serv_blueprint.add_url_rule("/influxdb_connectors", view_func=InfluxdbConnectorsList.as_view("influxdb_connectors"))

serv_blueprint.add_url_rule("/tasks/<service_name>", view_func=ServicesTasksListView.as_view("service_tasks"))
