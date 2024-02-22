"""
Infrastructure blueprint
"""
from flask import Blueprint
from flask_admin import expose
from flask_admin.contrib.sqla import ModelView
from openfactory.datafabric.app import admin
from openfactory.datafabric.app import db
from openfactory.models.nodes import Node


# Authentification blueprint
bp = Blueprint('infra', __name__,
               template_folder='templates' )

# Register models to admin app
admin.add_view(ModelView(Node, db.session))

from . import routes
