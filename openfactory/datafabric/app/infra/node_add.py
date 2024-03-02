"""
DataFabric Node add view
"""
import socket
import docker
from docker.errors import DockerException
from paramiko.ssh_exception import BadHostKeyException, AuthenticationException, SSHException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from flask import render_template
from flask import redirect
from flask import url_for
from flask import flash
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, IPAddress, ValidationError
from flask.views import MethodView

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
        db = create_engine(config.SQL_ALCHEMY_CONN)
        session = Session(db)
        if session.query(Node.id).filter_by(node_name=field.data).first() is not None:
            raise ValidationError("This name is already in use")

    def validate_node_ip(form, field):
        """ Validate node IP """
        if 'node_ip' in form.errors:
            return
        db = create_engine(config.SQL_ALCHEMY_CONN)
        session = Session(db)
        if session.query(Node.id).filter_by(node_ip=field.data).first() is not None:
            raise ValidationError("This IP is already in use")
        session.close()

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
            db_engine = create_engine(config.SQL_ALCHEMY_CONN)
            session = Session(db_engine)
            node = Node(
                node_name=form.node_name.data,
                node_ip=form.node_ip.data
            )
            session.add_all([node])
            session.commit()
            session.close()
            flash(f'Added new node {form.node_name.data}', "success")
            return redirect(url_for('infra.nodes'))
        else:
            flash('Cannot create the desired node. Some entries are not valid', "danger")
            return render_template("infra/nodes/node_add.html",
                                   form=form,
                                   title='Add Node')
