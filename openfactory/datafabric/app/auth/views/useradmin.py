from flask_admin.contrib.sqla import ModelView
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, ValidationError
from openfactory.datafabric.app import db
from openfactory.datafabric.app.auth.models.users import User


# Validators
def unique_username_validator(form, field):
    if db.session.query(User).filter_by(username=field.data).first():
        raise ValidationError("This username already exists. Please choose a different one.")


class UserForm(FlaskForm):
    """
    Custom form class for User
    """
    username = StringField('Username', validators=[DataRequired(), unique_username_validator])
    fullname = StringField('Full Name', validators=[DataRequired()])
    password = PasswordField('Password')


class UserModelView(ModelView):
    """
    Admin View of users
    """

    form = UserForm

    column_exclude_list = ['password_hash', ]

    def on_model_change(self, form, User, is_created):
        if form.password.data is not None:
            User.set_password(form.password.data)
