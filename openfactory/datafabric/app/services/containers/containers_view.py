"""
DataFabric Containers list view
"""
from sqlalchemy import select
from flask import render_template
from flask.views import View
from flask_login import login_required
from openfactory.models.containers import DockerContainer
from openfactory.datafabric.app import db


class ContainerList(View):
    """
    Containers list view
    """

    decorators = [login_required]

    def dispatch_request(self):
        query = select(DockerContainer)
        containers = db.session.scalars(query)
        return render_template("containers/containers_list.html",
                               containers=containers,
                               title='Containers')
