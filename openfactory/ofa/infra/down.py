import click
from sqlalchemy import select
from openfactory.ofa.db import db
from openfactory.utils import load_yaml
from openfactory.models.nodes import Node


@click.command(name='down')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def down(yaml_config_file):
    """ Tear down OpenFactory infrastructure """

    # Load yaml description file
    infra = load_yaml(yaml_config_file)

    for node, host in infra['nodes'].items():
        print("Detaching", node)
        query = select(Node).where(Node.node_name == node)
        for n in db.session.scalars(query):
            db.session.delete(n)
            db.session.commit()

    print("Shutting down manager")
    query = select(Node).where(Node.node_name == 'manager')
    for node in db.session.scalars(query):
        db.session.delete(node)
    db.session.commit()
