# app/auth/routes.py
import sqlalchemy as sa
from urllib.parse import urlsplit
from flask import request
from flask import render_template, flash, redirect, url_for
from flask_login import current_user, login_user, logout_user

from openfactory.datafabric.app import db
from openfactory.datafabric.app.auth.models.users import User
from openfactory.datafabric.app.auth import auth_blueprint
from openfactory.datafabric.app.auth.forms.loginform import LoginForm


@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login view
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', "danger")
            return redirect(url_for('auth.login'))
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@auth_blueprint.route('/logout')
def logout():
    """
    Logout view
    """
    logout_user()
    return redirect(url_for('main.index'))
