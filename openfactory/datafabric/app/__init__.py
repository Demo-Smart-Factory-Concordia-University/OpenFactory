"""
DataFabric WebApp
"""
from pathlib import Path
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
    app = Flask(__name__,
                instance_path=Config.INSTANCE_PATH)
    app.config.from_object(Config)

    # setup instance folder
    Path(Config.INSTANCE_PATH).mkdir(parents=True, exist_ok=True)
    
    db.init_app(app)

    # auth app
    login.init_app(app)
    login.login_message_category = "warning"
  
    # main blueprint
    from openfactory.datafabric.app.main import bp as main_blueprint
    app.register_blueprint(main_blueprint)

    # authentification blueprint
    from openfactory.datafabric.app.auth import bp as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    # infrastructure blueprint
    from openfactory.datafabric.app.infra import bp as infra_blueprint
    app.register_blueprint(infra_blueprint, url_prefix='/infra')

    # services blueprint
    from openfactory.datafabric.app.services import bp as services_blueprint
    app.register_blueprint(services_blueprint, url_prefix='/services')

    # admin app
    admin.init_app(app)
    admin.add_view(AgentView(Agent, db.session))
    admin.add_view(ModelView(DockerContainer, db.session))
    
    return app

from openfactory.models.compose import ComposeProject
from openfactory.models.agents import Agent
from openfactory.models.nodes import Node
from openfactory.models.containers import DockerContainer
from openfactory.datafabric.app.auth.models.users import User
