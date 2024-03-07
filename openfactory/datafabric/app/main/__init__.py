"""
DataFabric Main blueprint
"""
from flask import Blueprint

main_blueprint = Blueprint('main', __name__,
                           template_folder='templates',
                           static_folder='static',
                           static_url_path='/static/main')

def create_bp(app):
    """ Blueprint factory """
    # register blueprint
    app.register_blueprint(main_blueprint)

from . import routes
