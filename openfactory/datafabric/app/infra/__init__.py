"""
Infrastructure blueprint
"""
import os
from pathlib import Path
from flask import Blueprint


# Authentification blueprint
bp = Blueprint('infra', __name__,
               template_folder='templates' )

def create_bp(app):
    """ Blueprint factory """

    # register blueprint
    app.register_blueprint(bp, url_prefix='/infra')

from . import routes
