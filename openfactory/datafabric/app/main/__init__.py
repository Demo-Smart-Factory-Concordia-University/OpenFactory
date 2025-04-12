"""
DataFabric Main blueprint
"""
from flask import Blueprint
from openfactory.datafabric.app import admin_app, db
from openfactory.datafabric.app.main.models.notifications import Notification
from openfactory.datafabric.app.main.models.tasks import RQTask
from openfactory.datafabric.app.main.views.notificationview import NotificationView
from openfactory.datafabric.app.main.views.taskview import RQTaskView

main_blueprint = Blueprint('main', __name__,
                           template_folder='templates',
                           static_folder='static',
                           static_url_path='/static/main')

def create_bp(app):
    """ Blueprint factory """
    # register models to admin app
    admin_app.add_view(RQTaskView(RQTask, db.session, name='RQ-Task'))
    admin_app.add_view(NotificationView(Notification, db.session, name='User Notifications'))

    # register blueprint
    app.register_blueprint(main_blueprint)

from openfactory.datafabric.app.main import routes
