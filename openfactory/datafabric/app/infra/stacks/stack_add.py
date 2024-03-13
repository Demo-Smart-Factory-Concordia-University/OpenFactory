import os
import yaml
from flask import flash
from flask import render_template
from flask import redirect
from flask import url_for
from flask.views import MethodView
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import SubmitField
from wtforms.validators import ValidationError

from openfactory.utils import get_configuration


class StackAddForm(FlaskForm):
    """
    Infrastructure stack add form
    """
    yml_file = FileField('Infrastructure Stack YAML configuration file', validators=[FileRequired()])
    submit = SubmitField('Add Infrastructure Stack')

    def validate_yml_file(form, field):
        """ Validate that uploaded file is a YAML file """
        datastore_system = get_configuration('datastore_system')
        if datastore_system is None:
            raise ValidationError("Administrator needs to configure the 'datastore_system' variable")
        try:
            yaml.safe_load(field.data)
        except (yaml.YAMLError, UnicodeDecodeError):
            raise ValidationError("The file does not seem to be a YAML file")


class StackAdd(MethodView):
    """
    Stack add view
    """

    decorators = [login_required]
    methods = ["GET", "POST"]

    def get(self):
        # checks if required configuration is set by administrator
        if get_configuration('datastore_system') is None:
            flash("Cannot create Docker Compose projects. Administrator needs first to configure the 'datastore_system' variable", "danger")
            return redirect(url_for('infra.stacks'))
        form = StackAddForm()
        return render_template("infra/stacks/stack_add.html",
                               form=form,
                               title='Add Infrastructure Stack')

    def post(self):
        form = StackAddForm()
        if form.validate_on_submit():
            f = form.yml_file.data
            f.seek(0)
            stack_config_file = os.path.join(get_configuration('datastore_system'), 'stack_config_file.yml')
            f.save(stack_config_file)
            current_user.submit_RQ_task('add_stack',
                                        'Setting up infrastructure stack (this may take a while) ...',
                                        stack_config_file)
            return redirect(url_for('infra.home'))
        else:
            flash('Cannot create the infrastructure stack. Some entries are not valid', "danger")
            return render_template("infra/stacks/stack_add.html",
                                   form=form,
                                   title='Add Infrastructure Stack')
