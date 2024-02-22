"""
Authentification blueprint
"""
from flask import Blueprint
from flask_admin import expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import SecureForm
from wtforms import PasswordField
from openfactory.datafabric.app import admin
from openfactory.datafabric.app import db
from .models.users import User


# Admin views

class UserAdmin(ModelView):
    """ Admin View of users """
    form_base_class = SecureForm
    form_excluded_columns = ('password_hash')
    form_extra_fields = {
        'password': PasswordField('Password')
    }
    
    column_exclude_list = ['password_hash', ]
    
    def on_model_change(self, form, User, is_created):
        if form.password.data is not None:
            User.set_password(form.password.data)


# Authentification blueprint
bp = Blueprint('auth', __name__,
               template_folder='templates' )

# Register models to admin app
admin.add_view(UserAdmin(User, db.session))

from . import routes
