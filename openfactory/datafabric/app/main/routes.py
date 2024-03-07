"""
Routes for DataFabric Main Blueprint
"""
from flask_login import login_required
from flask import render_template
from . import main_blueprint


@main_blueprint.route('/')
@main_blueprint.route('/index')
@login_required
def index():
    return render_template('index.html',
                           title='Home')
