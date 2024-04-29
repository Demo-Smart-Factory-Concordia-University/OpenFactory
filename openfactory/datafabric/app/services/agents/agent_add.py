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
from wtforms import IntegerField, DecimalField, StringField, SubmitField
from wtforms_sqlalchemy.fields import QuerySelectField
from wtforms.validators import DataRequired, IPAddress, Regexp, NumberRange, Optional, ValidationError
from flask.views import MethodView

from openfactory.datafabric.app import db
from openfactory.models.configurations import get_configuration
from openfactory.models.agents import Agent
from openfactory.models.nodes import Node


def nodes():
    query = select(Node)
    return db.session.scalars(query)


class AgentAddForm(FlaskForm):
    """
    Agent add form
    """
    node = QuerySelectField(query_factory=nodes,
                            description='Node on which agent will be deployed')
    port = IntegerField('Agent port',
                        description='Port where agent will listen',
                        validators=[DataRequired()])
    device_uuid = StringField('Device UUID',
                              description='UUID of device agent handels',
                              validators=[DataRequired(),
                                          Regexp(r'^[a-zA-Z0-9-_]+$',
                                          message='Please use a single word with only alphanumeric characters and numbers')])
    mtc_file = FileField('MTConnect XML device model file',
                         description='MTConnect device model file',
                         validators=[FileRequired()])
    adapter_ip = StringField('Adapter IP',
                             description='IP address of adatper',
                             validators=[DataRequired(),
                                         IPAddress(ipv4=True, ipv6=False,
                                                   message="Please Enter a valid IP Address")])
    adapter_port = IntegerField('Adapter port',
                                description='Port where the adapter listens',
                                validators=[DataRequired()])
    agent_cpus = DecimalField('Allocated CPUs for Agent (leave empty or zero for maximum)',
                              description='CPUs allocated (can be fractions e.g. 0.5)',
                              validators=[Optional(),
                                          NumberRange(min=0,
                                                      message='Number of CPUS cannot be negative')])
    agent_memory = DecimalField('Allocated memory in Giga Bytes for Agent (leave empty or zero for maximum)',
                                description='Maximal memory allocated (in GB)',
                                validators=[Optional()])
    producer_cpus = DecimalField('Allocated CPUs for Kafka producer (leave empty or zero for maximum)',
                                 description='CPUs allocated (can be fractions e.g. 0.5)',
                                 validators=[NumberRange(min=0,
                                                         message='Number of CPUS cannot be negative')])
    producer_memory = DecimalField('Allocated memory in Giga Bytes for Kafka producer (leave empty or zero for maximum)',
                                   description='Maximal memory allocated (in GB)',
                                   validators=[Optional()])

    submit = SubmitField('Deploy Agent')

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

    def validate_agent_cpus(form, field):
        """ Validate number of CPUs is less than number of CPUs of node """
        node = form.node.data
        if field.data > node.cpus:
            raise ValidationError(f"Must be less than number of CPUs of deployment node ({node.cpus} cpus)")

    def validate_producer_cpus(form, field):
        """ Validate number of CPUs is less than number of CPUs of node """
        node = form.node.data
        if field.data > node.cpus:
            raise ValidationError(f"Must be less than number of CPUs of deployment node ({node.cpus} cpus)")


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
                               title='Deploy New Agent')

    def post(self):
        form = AgentAddForm()
        if form.validate_on_submit():

            agent = Agent(
                uuid=form.device_uuid.data.upper() + '-AGENT',
                external=False,
                agent_port=form.port.data,
                node_id=form.node.data.id,
            )

            current_user.submit_RQ_task('agent_up',
                                        f'Deploying MTConnect agent {form.device_uuid.data.upper()} on {form.node.data} (this may take a while) ...',
                                        agent,
                                        form.adapter_ip.data,
                                        form.adapter_port.data,
                                        os.path.join(get_configuration('datastore_system'), 'device.xml'),
                                        float(form.agent_cpus.data),
                                        float(form.producer_cpus.data))
            return redirect(url_for('services.agents'))
        else:
            flash('Cannot create the desired agent. Some entries are not valid', "danger")
            return render_template("services/agents/agent_add.html",
                                   form=form,
                                   title='Deploy New Agent')
