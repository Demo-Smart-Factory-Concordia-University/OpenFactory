"""
DataFabric Agents list view
"""
from sqlalchemy import select
from flask import render_template
from flask.views import View
from flask_login import login_required
from openfactory.models.agents import Agent
from openfactory.datafabric.app import db


class AgentList(View):
    """
    Agents list view
    """

    decorators = [login_required]

    def dispatch_request(self):
        query = select(Agent)
        agents = db.session.scalars(query)
        return render_template("services/agents/agents_list.html",
                               agents=agents,
                               title='Agents')
