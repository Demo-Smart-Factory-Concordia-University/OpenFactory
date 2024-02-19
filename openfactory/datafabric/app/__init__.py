"""
DataFabric WebApp
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from openfactory.models.base import Base
from openfactory.datafabric.config import Config
from openfactory.datafabric.app.admin.agentview import AgentView


db = SQLAlchemy(model_class=Base)
admin = Admin(name='DataFabric', template_mode='bootstrap3')

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    
    # main blueprint
    from openfactory.datafabric.app.main import bp as main_blueprint
    app.register_blueprint(main_blueprint)

    # admin app
    admin.init_app(app)
    admin.add_view(ModelView(Node, db.session))
    admin.add_view(AgentView(Agent, db.session))
    admin.add_view(ModelView(DockerContainer, db.session))
    
    return app

from openfactory.models.agents import Agent
from openfactory.models.nodes import Node
from openfactory.models.containers import DockerContainer
