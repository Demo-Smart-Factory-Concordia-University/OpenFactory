"""
Routes for DataFabric Main Blueprint
"""
from flask_login import login_required, current_user
from flask import render_template
from . import main_blueprint


@main_blueprint.route('/')
@main_blueprint.route('/index')
@login_required
def index():
    """ Home page of DataFabric """
    return render_template('index.html',
                           title='Home')


@main_blueprint.route('/rq_tasks')
@login_required
def rq_tasks():
    """ Returns all rq-tasks in progress of current user """
    tasks = current_user.get_RQ_tasks_in_progress()
    return [{'name': t.name,
             'id': t.id,
             'description': t.description} for t in tasks]


@main_blueprint.route('/new_user_notifications')
@login_required
def new_user_notifications():
    """ Returns 1 if new notifications 0 if none """
    notifications = current_user.count_notifications()
    print(notifications)
    if notifications > 0:
        return '1'
    else:
        return '0'


@main_blueprint.route('/user_notifications')
@login_required
def user_notifications():
    """ Returns all user notifications and clears them """
    notifications = current_user.get_notifications()
    current_user.clear_notifications()
    return [{'message': n.message,
             'type': n.type} for n in notifications]
