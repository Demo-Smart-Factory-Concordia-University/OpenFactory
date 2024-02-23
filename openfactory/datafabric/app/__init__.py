"""
DataFabric WebApp
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from openfactory.models.base import Base
from openfactory.datafabric.config import Config
from openfactory.datafabric.app.admin.agentview import AgentView


db = SQLAlchemy(model_class=Base)
login = LoginManager()
login.login_view = 'auth.login'
admin = Admin(name='DataFabric', template_mode='bootstrap3')

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)

    # auth app
    login.init_app(app)
  
    # main blueprint
    from openfactory.datafabric.app.main import bp as main_blueprint
    app.register_blueprint(main_blueprint)

    # authentification blueprint
    from openfactory.datafabric.app.auth import bp as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    # infrastructure blueprint
    from openfactory.datafabric.app.infra import bp as infra_blueprint
    app.register_blueprint(infra_blueprint, url_prefix='/infra')

    # admin app
    admin.init_app(app)
    admin.add_view(AgentView(Agent, db.session))
    admin.add_view(ModelView(DockerContainer, db.session))
    
    return app


from openfactory.models.agents import Agent
from openfactory.models.nodes import Node
from openfactory.models.containers import DockerContainer
from openfactory.datafabric.app.auth.models.users import User