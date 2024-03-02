import click
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from openfactory.utils import load_yaml
from openfactory.models.nodes import Node
import openfactory.config as config


@click.command(name='down')
@click.argument('yaml_config_file',
                type=click.Path(exists=True),
                nargs=1)
def down(yaml_config_file):
    """ Tear down OpenFactory infrastructure """

    db_engine = create_engine(config.SQL_ALCHEMY_CONN)
    session = Session(db_engine)

    # Load yaml description file
    infra = load_yaml(yaml_config_file)

    for node, host in infra['nodes'].items():
        print("Detaching", node)
        query = select(Node).where(Node.node_name == node)
        for n in session.scalars(query):
            session.delete(n)
            session.commit()

    print("Shutting down manager")
    query = select(Node).where(Node.node_name == 'manager')
    for node in session.scalars(query):
        session.delete(node)

    session.commit()
    session.close()
