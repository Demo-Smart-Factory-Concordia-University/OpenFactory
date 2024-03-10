from flask import redirect
from flask import url_for
from flask.views import View
from flask_login import login_required, current_user

from openfactory.datafabric.app import db
from openfactory.models.compose import ComposeProject


class ComposeRemove(View):
    """
    Remove a Docker Compose project
    """

    decorators = [login_required]

    def dispatch_request(self, compose_id):
        """ Remove Docker Compose project """

        query = db.session.query(ComposeProject).where(ComposeProject.id == compose_id)
        compose = db.session.execute(query).one()
        compose = compose[0]
        current_user.submit_RQ_task('compose_down',
                                    'Tearing down Docker Compose project ' + compose.name + ' (this may take a while) ...',
                                    compose)
        return redirect(url_for('infra.compose_list'))
