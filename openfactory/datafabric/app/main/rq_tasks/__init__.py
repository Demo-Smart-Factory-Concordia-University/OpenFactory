from openfactory.datafabric.app import create_app

app = create_app()
app.app_context().push()

from .node_up import node_up
from .node_down import node_down
from .compose_up import compose_up
from .compose_down import compose_down
from .add_stack import add_stack
from .agent_up import agent_up
from .agent_down import agent_down
from .load_agent_stack import load_agent_stack
