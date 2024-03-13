from openfactory.datafabric.app import create_app

app = create_app()
app.app_context().push()

from .node_up import node_up
from .node_down import node_down
from .compose_up import compose_up
from .compose_down import compose_down
from .remove_stack import remove_stack
from .add_stack import add_stack
