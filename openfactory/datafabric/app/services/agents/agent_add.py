"""
DataFabric Agent add view
"""
import os
import socket
import xml.etree.ElementTree as ET
from sqlalchemy import select
from flask import flash
from flask import render_template
from flask import redirect
from flask import url_for
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import IntegerField, StringField, SubmitField
from wtforms_sqlalchemy.fields import QuerySelectField
from wtforms.validators import DataRequired, IPAddress, Regexp, ValidationError
from flask.views import MethodView

import openfactory.config as config
from openfactory.datafabric.app import db
from openfactory.utils import get_configuration
from openfactory.models.agents import Agent
from openfactory.models.containers import DockerContainer, EnvVar, Port
from openfactory.models.nodes import Node


def nodes():
    query = select(Node)
    return db.session.scalars(query)


class AgentAddForm(FlaskForm):
    """
    Agent add form
    """
    node = QuerySelectField(query_factory=nodes)
    port = IntegerField('Agent port',
                        validators=[DataRequired()])
    device_uuid = StringField('Device UUID',
                              validators=[DataRequired(),
                                          Regexp(r'^[a-zA-Z0-9-_]+$',
                                          message='Please use a single word with only alphanumeric characters and numbers')])
    mtc_file = FileField('MTConnect XML device model file',
                         validators=[FileRequired()])
    adapter_ip = StringField('Adapter IP',
                             validators=[DataRequired(),
                                         IPAddress(ipv4=True, ipv6=False,
                                                   message="Please Enter a valid IP Address")])
    adapter_port = IntegerField('Adapter port',
                                validators=[DataRequired()])
    submit = SubmitField('Add Agent')

    def validate_device_uuid(form, field):
        """ Validate that device UUID is unique """
        if db.session.query(Agent).filter_by(uuid=field.data.upper()+'-AGENT').first() is not None:
            raise ValidationError(f"An agent for device UUID {field.data.upper()} exists already")

    def validate_adapter_ip(form, field):
        """ Validate adapter IP """
        if 'adapter_ip' in form.errors:
            return
        try:
            socket.gethostbyaddr(field.data)
        except socket.herror:
            raise ValidationError("This IP address can't be reached")

    def validate_mtc_file(form, field):
        """ Validate MTConnect device model file """
        datastore_system = get_configuration('datastore_system')
        if datastore_system is None:
            raise ValidationError("Administrator needs to configure the 'datastore_system' variable")
        field.data.seek(0)
        mtc_file = os.path.join(datastore_system, 'device.xml')
        field.data.save(mtc_file)
        try:
            ET.parse(mtc_file)
        except ET.ParseError:
            raise ValidationError('The file does not seem to be an XML file')


class AgentAdd(MethodView):
    """
    Agent add view
    """

    decorators = [login_required]
    methods = ["GET", "POST"]

    def get(self):
        # checks if required configuration is set by administrator
        if get_configuration('datastore_system') is None:
            flash("Cannot create MTConnect agents. Administrator needs first to configure the 'datastore_system' variable", "danger")
            return redirect(url_for('services.agents'))
        form = AgentAddForm()
        return render_template("services/agents/agent_add.html",
                               form=form,
                               title='Add Agent')

    def post(self):
        form = AgentAddForm()
        if form.validate_on_submit():

            # configure Docker container of agent
            container = DockerContainer(
                node_id=form.node.data.id,
                node=form.node.data,
                image=config.MTCONNECT_AGENT_IMAGE,
                name=form.device_uuid.data.lower() + '-agent',
                ports=[
                    Port(container_port='5000/tcp', host_port=form.port.data)
                ],
                environment=[
                    EnvVar(variable='MTC_AGENT_UUID', value=form.device_uuid.data.upper() + "-AGENT"),
                    EnvVar(variable='ADAPTER_UUID', value=form.device_uuid.data.upper()),
                    EnvVar(variable='ADAPTER_IP', value=form.adapter_ip.data),
                    EnvVar(variable='ADAPTER_PORT', value=form.adapter_port.data),
                    EnvVar(variable='DOCKER_GATEWAY', value='172.17.0.1')
                ],
                command='mtcagent run agent.cfg',
            )

            # configure agent
            agent = Agent(
                uuid=form.device_uuid.data.upper() + '-AGENT',
                external=False,
                agent_port=form.port.data,
                node_id=form.node.data.id,
                agent_container=container
            )

            current_user.submit_RQ_task('agent_up',
                                        f'Deploying MTConnect agent {form.device_uuid.data.upper()} on {form.node.data} (this may take a while) ...',
                                        agent, container,
                                        os.path.join(get_configuration('datastore_system'), 'device.xml'))
            return redirect(url_for('services.agents'))
        else:
            flash('Cannot create the desired agent. Some entries are not valid', "danger")
            return render_template("services/agents/agent_add.html",
                                   form=form,
                                   title='Add Agent')
