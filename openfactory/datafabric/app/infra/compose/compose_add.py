"""
DataFabric Docker Compose project add view
"""
import os
import yaml
from python_on_whales import DockerClient
from python_on_whales.exceptions import DockerException
from sqlalchemy import select
from flask import render_template
from flask import flash
from flask import redirect
from flask import url_for
from flask.views import MethodView
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Regexp, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectField

from openfactory.datafabric.app import db
from openfactory.models.configurations import get_configuration
from openfactory.models.compose import ComposeProject
from openfactory.models.nodes import Node


def nodes():
    query = select(Node)
    return db.session.scalars(query)


class ComposeAddForm(FlaskForm):
    """
    Docker Compose add form
    """
    node = QuerySelectField(query_factory=nodes,
                            description='Node on which Docker Compose porject will be deployed')
    name = StringField('Docker Compose project name',
                       description='Unique name for Docker Compose project',
                       validators=[DataRequired(),
                                   Regexp(r'^[\w]+$',
                                          message='Please use single word with only alphanumeric characters')])
    description = StringField('Description (optional)',
                              description='Optional description of Docker Compose project')
    yml_file = FileField('Docker Compose YAML configuration file',
                         description='Docker Compose YAML configuration file',
                         validators=[FileRequired()])
    submit = SubmitField('Add Docker Compose Project')

    def validate_name(form, field):
        """ Validate that compose project name is unique """
        if db.session.query(ComposeProject.id).filter_by(name=field.data).first() is not None:
            raise ValidationError("This name is already in use")

    def validate_yml_file(form, field):
        """ Validate that uploaded file is a Docker Compose YAML file """
        datastore_system = get_configuration('datastore_system')
        if datastore_system is None:
            raise ValidationError("Administrator needs to configure the 'datastore_system' variable")
        try:
            yaml.safe_load(field.data)
        except (yaml.YAMLError, UnicodeDecodeError):
            raise ValidationError("The file does not seem to be a YAML file")
        field.data.seek(0)
        compose_file = os.path.join(datastore_system, form.name.data + '.yml')
        field.data.save(compose_file)
        docker = DockerClient(compose_files=[compose_file])
        try:
            docker.compose.config()
        except DockerException:
            raise ValidationError("The file is not a valid Docker Compose config file")


class ComposeAdd(MethodView):
    """
    Docker Compose add view
    """

    decorators = [login_required]
    methods = ["GET", "POST"]

    def get(self):
        # checks if required configuration is set by administrator
        if get_configuration('datastore_system') is None:
            flash("Cannot create Docker Compose projects. Administrator needs first to configure the 'datastore_system' variable", "danger")
            return redirect(url_for('infra.compose_list'))
        form = ComposeAddForm()
        return render_template("infra/compose/compose_add.html",
                               form=form,
                               title='Add Compose Project')

    def post(self):
        form = ComposeAddForm()
        if form.validate_on_submit():
            f = form.yml_file.data
            f.seek(0)   # required because of the previous save in validation
            compose = ComposeProject(
                node=form.node.data,
                node_id=form.node.data.id,
                name=form.name.data,
                description=form.description.data,
                yaml_config=f.read().decode()
            )
            current_user.submit_RQ_task('compose_up',
                                        'Setting up Docker Compose project ' + form.name.data + ' (this may take a while) ...',
                                        compose)
            return redirect(url_for('infra.compose_list'))
        else:
            flash('Cannot create the Docker Compose project. Some entries are not valid', "danger")
            return render_template("infra/compose/compose_add.html",
                                   form=form,
                                   title='Add Compose Project')
