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

from openfactory.models.configurations import get_configuration


class LoadDevicesStackForm(FlaskForm):
    """
    Devices stack load form
    """
    yml_file = FileField('Devices Stack YAML configuration file',
                         description='Devices Stack YAML configuration file',
                         validators=[FileRequired()])
    submit = SubmitField('Load Devices Stack')

    def validate_yml_file(form, field):
        """ Validate that uploaded file is a YAML file """
        datastore_system = get_configuration('datastore_system')
        if datastore_system is None:
            raise ValidationError("Administrator needs to configure the 'datastore_system' variable")
        try:
            yaml.safe_load(field.data)
        except (yaml.YAMLError, UnicodeDecodeError):
            raise ValidationError("The file does not seem to be a YAML file")


class DeviceStackLoad(MethodView):
    """
    Stack add view
    """

    decorators = [login_required]
    methods = ["GET", "POST"]

    def get(self):
        # checks if required configuration is set by administrator
        if get_configuration('datastore_system') is None:
            flash("Cannot create agent stacks. Administrator needs first to configure the 'datastore_system' variable", "danger")
            return redirect(url_for('infra.stacks'))
        form = LoadDevicesStackForm()
        return render_template('services/devices/devices_load.html',
                               form=form,
                               title='Load Devices Stack')

    def post(self):
        form = LoadDevicesStackForm()
        if form.validate_on_submit():
            f = form.yml_file.data
            f.seek(0)
            stack_config_file = os.path.join(get_configuration('datastore_system'), 'stack_config_file.yml')
            f.save(stack_config_file)
            current_user.submit_RQ_task('load_agent_stack',
                                        'Setting up devices stack (this may take a while) ...',
                                        stack_config_file)
            return redirect(url_for('services.home'))
        else:
            flash('Cannot create the device stack. Some entries are not valid', 'danger')
            return render_template('Services/devices/devices_load.html',
                                   form=form,
                                   title='Load Devices Stack')
