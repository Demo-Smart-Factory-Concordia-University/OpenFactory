"""
DataFabric Stacks list view
"""
from sqlalchemy import select
from flask import render_template
from flask.views import View
from flask_login import login_required
from openfactory.models.infrastack import InfraStack
from openfactory.datafabric.app import db


class StacksList(View):
    """
    InfraStack list view
    """

    decorators = [login_required]

    def dispatch_request(self):
        query = select(InfraStack)
        stacks = db.session.scalars(query)
        return render_template("infra/stacks/stacks_list.html", stacks=stacks, title='Infrastructure Stacks')
