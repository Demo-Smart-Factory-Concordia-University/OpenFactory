"""
Services blueprint
"""
from flask import Blueprint
from flask_admin import expose
from flask_admin.contrib.sqla import ModelView
from openfactory.datafabric.app import admin
from openfactory.datafabric.app import db
from openfactory.models.nodes import Node


# Authentification blueprint
bp = Blueprint('services', __name__,
               template_folder='templates' )


from . import routes
