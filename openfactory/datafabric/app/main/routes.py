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
