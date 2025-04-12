"""
Routes for DataFabric Services Blueprint
"""
from flask_login import login_required
from flask import render_template
from openfactory.datafabric.app.services import serv_blueprint
from openfactory.datafabric.app.services.devices.devices_view import DevicesList
from openfactory.datafabric.app.services.devices.device_services import DeviceServicesList
from openfactory.datafabric.app.services.devices.device_add import DeviceAdd
from openfactory.datafabric.app.services.devices.device_remove import DeviceRemove
from openfactory.datafabric.app.services.devices.devices_load import DeviceStackLoad
from openfactory.datafabric.app.services.applications.apps_view import ApplicationsList
from openfactory.datafabric.app.services.agents.agents_view import AgentsList
from openfactory.datafabric.app.services.supervisors.supervisors_view import SupervisorsList
from openfactory.datafabric.app.services.producers.producers_view import ProducersList
from openfactory.datafabric.app.services.influxdb_connectors.influxdb_connectors_view import InfluxdbConnectorsList
from openfactory.datafabric.app.services.core.services_tasks_view import ServicesTasksListView
from openfactory.datafabric.app.services.core.service_task_logs import ServiceTaskLogs


@serv_blueprint.route('/')
@login_required
def home():
    return render_template('services/servicesBase.html',
                           title='Services')


serv_blueprint.add_url_rule("/devices", view_func=DevicesList.as_view("devices"))
serv_blueprint.add_url_rule("/device/services/<device_uuid>", view_func=DeviceServicesList.as_view("device_services_list"))
serv_blueprint.add_url_rule("/device/add", view_func=DeviceAdd.as_view("device_add"))
serv_blueprint.add_url_rule("/device/remove/<int:agent_id>", view_func=DeviceRemove.as_view("device_remove"))
serv_blueprint.add_url_rule("/device/load_stack", view_func=DeviceStackLoad.as_view("device_load_stack"))

serv_blueprint.add_url_rule("/apps", view_func=ApplicationsList.as_view("apps"))

serv_blueprint.add_url_rule("/agents", view_func=AgentsList.as_view("agents"))
serv_blueprint.add_url_rule("/supervisors", view_func=SupervisorsList.as_view("supervisors"))
serv_blueprint.add_url_rule("/producers", view_func=ProducersList.as_view("producers"))
serv_blueprint.add_url_rule("/influxdb_connectors", view_func=InfluxdbConnectorsList.as_view("influxdb_connectors"))

serv_blueprint.add_url_rule("/tasks/<service_name>", view_func=ServicesTasksListView.as_view("service_tasks"))
serv_blueprint.add_url_rule("/tasks/logs/<task_id>", view_func=ServiceTaskLogs.as_view("service_task_logs"))
