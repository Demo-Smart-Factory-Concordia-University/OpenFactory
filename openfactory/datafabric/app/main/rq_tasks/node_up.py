"""
RQ Task to create a new OpenFactory Node
"""
from rq import get_current_job
from openfactory.models.nodes import Node
from openfactory.datafabric.app import db, create_app
from openfactory.datafabric.app.main.models.tasks import RQTask


app = create_app()
app.app_context().push()


def node_up(node_name, node_ip):
    """ Spins up an OpenFactory node """

    # create new node
    node = Node(
        node_name=node_name,
        node_ip=node_ip
    )
    db.session.add_all([node])
    db.session.commit()

    # clear rq-task
    job = get_current_job()
    rq_task = db.session.get(RQTask, job.get_id())
    rq_task.complete = True
    rq_task.user.send_notification(f'Added new node {node_name}', "success")
    db.session.commit()
