"""
DataFabric WebApp
"""
import rq
from redis import Redis
from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from openfactory.models.base import Base
from openfactory.docker.docker_access_layer import dal
from openfactory.datafabric.config import Config
from openfactory.datafabric.app.admin.agentview import AgentView
from openfactory.datafabric.app.admin.composeview import ComposeProjectView


db = SQLAlchemy(model_class=Base)
admin = Admin(name='DataFabric', template_mode='bootstrap3')

def create_app(config_class=Config):
    app = Flask(__name__,
                instance_path=Config.INSTANCE_PATH)
    app.config.from_object(Config)

    # setup instance folder
    Path(Config.INSTANCE_PATH).mkdir(parents=True, exist_ok=True)

    # Redis and RQ
    app.redis = Redis.from_url(Config.REDIS_URL)
    app.task_queue = rq.Queue('datafabric-tasks', connection=app.redis)

    # Docker access layer
    dal.connect()

    db.init_app(app)

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

    # admin app
    admin.init_app(app)
    admin.add_view(ModelView(ofamodels.Configuration, db.session))
    admin.add_view(AgentView(ofamodels.Agent, db.session))
    admin.add_view(ModelView(ofamodels.Node, db.session))
    admin.add_view(ComposeProjectView(ofamodels.ComposeProject, db.session))
    
    return app

import openfactory.models as ofamodels
import openfactory.datafabric.app.main.models
import openfactory.datafabric.app.auth.models
