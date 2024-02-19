# app/main/routes.py

from flask import render_template
from . import bp


@bp.route('/')
@bp.route('/index')
def index():
    user = {'username': 'Bob'}
    return render_template('index.html',
                           title='Home',
                           user=user)
