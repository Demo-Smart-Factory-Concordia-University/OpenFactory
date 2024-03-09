"""
DataFabric Main blueprint
"""
from flask import Blueprint
from openfactory.datafabric.app import admin, db
from .models.notifications import Notification
from .models.tasks import RQTask
from .views.notificationview import NotificationView
from .views.taskview import RQTaskView

main_blueprint = Blueprint('main', __name__,
                           template_folder='templates',
                           static_folder='static',
                           static_url_path='/static/main')

def create_bp(app):
    """ Blueprint factory """
    # register models to admin app
    admin.add_view(RQTaskView(RQTask, db.session, name='RQ-Task'))
    admin.add_view(NotificationView(Notification, db.session, name='User Notifications'))

    # register blueprint
    app.register_blueprint(main_blueprint)

from . import routes
