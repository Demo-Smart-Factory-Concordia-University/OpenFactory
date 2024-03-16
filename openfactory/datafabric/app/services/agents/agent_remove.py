from flask.views import View
from flask import redirect
from flask import url_for
from flask_login import login_required, current_user

from openfactory.datafabric.app import db
from openfactory.models.agents import Agent


class AgentRemove(View):
    """
    Remove and Agent and its related containers
    """

    decorators = [login_required]

    def dispatch_request(self, agent_id):

        query = db.session.query(Agent).where(Agent.id == agent_id)
        agent = db.session.execute(query).one()
        agent = agent[0]
        current_user.submit_RQ_task('agent_down',
                                    'Tearing down Agent ' + agent.uuid + ' (this may take a while) ...',
                                    agent)
        return redirect(url_for('services.home'))
