from flask.views import View
from flask import flash
from flask import redirect
from flask import url_for
from flask_login import login_required, current_user

from openfactory.docker.docker_access_layer import dal


class NodeRemove(View):

    decorators = [login_required]

    def dispatch_request(self, node_id):

        client = dal.docker_client
        node = client.nodes.get(node_id)

        if node.attrs.get('Spec', {}).get('Role') == 'manager':
            flash('Cannot remove manger node', "danger")
            return redirect(url_for('infra.nodes'))

        current_user.submit_RQ_task('node_down',
                                    'Removing node ' + node.attrs['Description']['Hostname'] + '...',
                                    node_id)

        return redirect(url_for('infra.home'))
