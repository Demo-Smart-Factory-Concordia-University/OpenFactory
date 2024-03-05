"""
Infrastructure blueprint
"""
import os
from pathlib import Path
from flask import current_app
from flask import Blueprint
from flask_admin import expose
from flask_admin.contrib.sqla import ModelView
from openfactory.datafabric.app import admin
from openfactory.datafabric.app import db
from openfactory.models.compose import ComposeProject
from openfactory.models.nodes import Node
from openfactory.datafabric.config import Config


# Authentification blueprint
bp = Blueprint('infra', __name__,
               template_folder='templates' )

# Register models to admin app
admin.add_view(ModelView(Node, db.session))
admin.add_view(ModelView(ComposeProject, db.session))

# setup instance folder
Path(os.path.join(Config.INSTANCE_PATH, 'docker_compose')).mkdir(parents=True, exist_ok=True)

from . import routes
