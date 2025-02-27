"""
DataFabric WebApp
"""
import rq
from redis import Redis
from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from pyksql.ksql import KSQL
from openfactory.models.base import Base
from openfactory.docker.docker_access_layer import dal
from openfactory.datafabric.config import Config
import openfactory.datafabric.filters as filters

db = SQLAlchemy(model_class=Base)
admin_app = Admin(name='DataFabric', template_mode='bootstrap3')
ksql = KSQL(Config.KSQL_HOST)

def create_app():
    app = Flask(__name__,
                instance_path=Config.INSTANCE_PATH)
    app.config.from_object(Config)

    # jinja filters
    app.jinja_env.filters['availability_color'] = filters.availability_color
    app.jinja_env.filters['connection_status_color'] = filters.connection_status_color

    # setup instance folder
    Path(Config.INSTANCE_PATH).mkdir(parents=True, exist_ok=True)

    # Redis and RQ
    app.redis = Redis.from_url(Config.REDIS_URL)
    app.task_queue = rq.Queue('datafabric-tasks', connection=app.redis)

    # Docker access layer
    dal.connect()

    # Initialize extensions with the app context
    db.init_app(app)
    admin_app.init_app(app)

    with app.app_context():
        db.create_all()

    # admin app views
    from openfactory.datafabric.app.admin.configurationview import ConfigurationModelView
    from openfactory.models.configurations import Configuration
    admin_app.add_view(ConfigurationModelView(Configuration, db.session))

    from openfactory.models.agents import Agent
    from openfactory.datafabric.app.admin.agentview import AgentView
    admin_app.add_view(AgentView(Agent, db.session))

    # main blueprint
    from openfactory.datafabric.app.main import create_bp as create_main_bp
    create_main_bp(app)

    # authentification blueprint
    from openfactory.datafabric.app.auth import create_bp as create_auth_bp
    create_auth_bp(app)

    # infrastructure blueprint
    from openfactory.datafabric.app.infra import create_bp as create_infra_bp
    create_infra_bp(app)

    # services blueprint
    from openfactory.datafabric.app.services import create_bp as create_services_bp
    create_services_bp(app)
    
    return app

import openfactory.datafabric.app.auth.models
