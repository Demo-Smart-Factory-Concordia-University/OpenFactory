"""
DataFabric Compose project add view
"""
import os
from sqlalchemy import select
from flask import current_app
from flask import render_template
from flask import flash
from flask import redirect
from flask import url_for
from flask.views import MethodView
from flask_login import login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Regexp
from wtforms_sqlalchemy.fields import QuerySelectField

from openfactory.datafabric.app import db
from openfactory.models.compose import ComposeProject
from openfactory.models.nodes import Node


def nodes():
    query = select(Node)
    return db.session.scalars(query)


class ComposeAddForm(FlaskForm):
    """
    Docker Compose add form
    """
    node = QuerySelectField(query_factory=nodes)
    name = StringField('Docker Compose project name',
                       validators=[DataRequired(),
                                   Regexp(r'^[\w]+$',
                                          message='Please use single word with only alphanumeric characters')])
    description = StringField('Description (optional)')
    yml_file = FileField('Docker Compose YAML configuration file', validators=[FileRequired()])

    submit = SubmitField('Add Docker Compose Project')


class ComposeAdd(MethodView):
    """
    Docker Compose add view
    """

    decorators = [login_required]
    methods = ["GET", "POST"]

    def get(self):
        form = ComposeAddForm()
        return render_template("infra/compose/compose_add.html",
                               form=form,
                               title='Add Compose Project')

    def post(self):
        form = ComposeAddForm()
        if form.validate_on_submit():
            f = form.yml_file.data
            f.save(os.path.join(current_app.instance_path, 'docker_compose', form.name.data + '.yml'))
            f.seek(0)   # required because of the previous save
            compose = ComposeProject(
                node=form.node.data,
                node_id=form.node.data.id,
                name=form.name.data,
                description=form.description.data,
                yaml_config=f.read().decode()
            )
            db.session.add_all([compose])
            db.session.commit()

            flash(f'Added new Docker Compose project {form.name.data}', "success")
            return redirect(url_for('infra.nodes'))
        else:
            flash('Cannot create the Docker Compose project. Some entries are not valid', "danger")
            return render_template("infra/compose/compose_add.html",
                                   form=form,
                                   title='Add Compose Project')
