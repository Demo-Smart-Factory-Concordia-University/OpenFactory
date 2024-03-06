"""
DataFabric Main blueprint
"""
from flask import Blueprint
from flask_admin.contrib.sqla import ModelView
from openfactory.datafabric.app import admin
from openfactory.models.configurations import Configuration
from openfactory.datafabric.app import db

bp = Blueprint('main', __name__,
               template_folder='templates',
               static_folder='static',
               static_url_path='/static/main')

# Register models to admin app
admin.add_view(ModelView(Configuration, db.session))

from . import routes
