from flask_admin.contrib.sqla import ModelView
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, ValidationError
from openfactory.models.configurations import Configuration
from openfactory.datafabric.app import db


# Custom validator for the key field
def unique_key_validator(form, field):
    if db.session.query(Configuration).filter_by(key=field.data).first():
        raise ValidationError("This key already exists. Please choose a different key.")


class ConfigurationForm(FlaskForm):
    """
    Custom form class for Configuration
    """
    key = StringField('Key', validators=[DataRequired(), unique_key_validator])
    value = TextAreaField('Value', validators=[DataRequired()])
    description = TextAreaField('Description')


class ConfigurationModelView(ModelView):
    """
    Admin View for Configuration Model
    """
    form = ConfigurationForm
