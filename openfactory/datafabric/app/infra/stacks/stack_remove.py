from flask import redirect
from flask import url_for
from flask.views import View
from flask_login import login_required, current_user
from openfactory.datafabric.app import db
from openfactory.models.infrastack import InfraStack


class StackRemove(View):

    decorators = [login_required]

    def dispatch_request(self, stack_id):
        query = db.session.query(InfraStack).where(InfraStack.id == stack_id)
        stack = db.session.execute(query).one()
        stack = stack[0]
        stack_name = stack.stack_name
        current_user.submit_RQ_task('remove_stack',
                                    'Removing stack ' + stack_name + '...',
                                    stack.id)
        return redirect(url_for('infra.home'))
