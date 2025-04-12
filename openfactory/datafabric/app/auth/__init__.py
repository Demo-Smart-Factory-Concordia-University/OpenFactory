"""
Authentification blueprint
"""
from flask import Blueprint
from flask_login import LoginManager
from openfactory.datafabric.app import admin_app
from openfactory.datafabric.app import db
from openfactory.datafabric.app.auth.models.users import User
from openfactory.datafabric.app.auth.views.useradmin import UserModelView


# Login manager
login = LoginManager()

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))

# blueprint
auth_blueprint = Blueprint('auth', __name__,
                           template_folder='templates')

def create_bp(app):
    """ Blueprint factory """
    # register models to admin app
    admin_app.add_view(UserModelView(User, db.session))

    # configure LoginManager
    login.login_view = 'auth.login'
    login.login_message_category = "warning"
    login.init_app(app)

    # register blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

from openfactory.datafabric.app.auth import routes
