"""
DataFabric Compose Projects list view
"""
from sqlalchemy import select
from flask import render_template
from flask.views import View
from flask_login import login_required
from openfactory.models.compose import ComposeProject
from openfactory.datafabric.app import db


class ComposeProjecList(View):
    """
    ComposeProject list view
    """

    decorators = [login_required]

    def dispatch_request(self):
        query = select(ComposeProject)
        compose_projects = db.session.scalars(query)
        return render_template("infra/compose/compose_list.html",
                               projects=compose_projects,
                               title='Docker Compose Projects')
