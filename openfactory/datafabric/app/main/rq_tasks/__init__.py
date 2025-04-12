from openfactory.datafabric.app import create_app

app = create_app()
app.app_context().push()

from openfactory.datafabric.app.main.rq_tasks.node_up import node_up
from openfactory.datafabric.app.main.rq_tasks.node_down import node_down
from openfactory.datafabric.app.main.rq_tasks.compose_up import compose_up
from openfactory.datafabric.app.main.rq_tasks.compose_down import compose_down
from openfactory.datafabric.app.main.rq_tasks.add_stack import add_stack
from openfactory.datafabric.app.main.rq_tasks.agent_up import agent_up
from openfactory.datafabric.app.main.rq_tasks.agent_down import agent_down
from openfactory.datafabric.app.main.rq_tasks.load_agent_stack import load_agent_stack
