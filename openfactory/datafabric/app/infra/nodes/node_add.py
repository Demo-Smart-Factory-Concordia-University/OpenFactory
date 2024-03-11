"""
DataFabric Node add view
"""
import socket
import docker
from docker.errors import DockerException
from paramiko.ssh_exception import BadHostKeyException, AuthenticationException, SSHException
from flask import render_template
from flask import redirect
from flask import url_for
from flask import flash
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, IPAddress, ValidationError
from flask.views import MethodView

from openfactory.datafabric.app import db
from openfactory.models.nodes import Node
import openfactory.config as config


class NodeAddForm(FlaskForm):
    """
    Node add form
    """
    node_name = StringField('Node name', validators=[DataRequired()])
    node_ip = StringField('Node IP',
                          validators=[DataRequired(),
                                      IPAddress(ipv4=True, ipv6=False,
                                                message="Please Enter a valid IP Address")])
    submit = SubmitField('Add Node')

    def validate_node_name(form, field):
        """ Validate that node name is unique """
        if db.session.query(Node.id).filter_by(node_name=field.data).first() is not None:
            raise ValidationError("This name is already in use")

    def validate_node_ip(form, field):
        """ Validate node IP """
        if 'node_ip' in form.errors:
            return
        if db.session.query(Node.id).filter_by(node_ip=field.data).first() is not None:
            raise ValidationError("This IP is already in use")

        try:
            socket.gethostbyaddr(field.data)
        except socket.herror:
            raise ValidationError("This IP address can't be reached")

        try:
            client = docker.DockerClient(base_url='ssh://' + config.OPENFACTORY_USER + '@' + field.data)
        except (BadHostKeyException,
                AuthenticationException,
                SSHException,
                DockerException):
            raise ValidationError(f"The OpenFactory user '{config.OPENFACTORY_USER}' cannot use Docker on this node")
        client.close()


class NodeAdd(MethodView):
    """
    Node add view
    """

    decorators = [login_required]
    methods = ["GET", "POST"]

    def get(self):
        form = NodeAddForm()
        return render_template("infra/nodes/node_add.html",
                               form=form,
                               title='Add Node')

    def post(self):
        form = NodeAddForm()
        if form.validate_on_submit():
            task = current_user.submit_RQ_task('node_up',
                                               'Setting up node ' + form.node_name.data + ' ...',
                                               form.node_name.data,
                                               form.node_ip.data)
            # wait task is done
            while task.get_rq_job().result is None:
                pass
            if task.get_rq_job().result:
                flash(f'Added successfully node {form.node_name.data}', "success")
            return redirect(url_for('infra.home'))
        else:
            flash('Cannot create the desired node. Some entries are not valid', "danger")
            return render_template("infra/nodes/node_add.html",
                                   form=form,
                                   title='Add Node')
