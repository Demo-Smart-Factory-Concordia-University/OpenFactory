"""
Services blueprint
"""
from flask import Blueprint


# Service blueprint
bp = Blueprint('services', __name__,
               template_folder='templates' )

def create_bp(app):
    """ Blueprint factory """
    # register blueprint
    app.register_blueprint(bp, url_prefix='/services')

from . import routes
