"""
Infrastructure blueprint
"""
from flask import Blueprint


# Infrastructure blueprint
infra_blueprint = Blueprint('infra', __name__,
                            template_folder='templates' )

def create_bp(app):
    """ Blueprint factory """
    # register blueprint
    app.register_blueprint(infra_blueprint, url_prefix='/infra')

from openfactory.datafabric.app.infra import routes
