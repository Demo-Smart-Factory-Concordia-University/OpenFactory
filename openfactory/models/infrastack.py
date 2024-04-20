from typing import List
from sqlalchemy import event
from sqlalchemy import String
from sqlalchemy.orm import Session
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from openfactory.exceptions import OFAException
from .user_notifications import user_notify
from .base import Base
from .nodes import Node


class InfraStack(Base):
    """
    OpenFactory Infrastructure Stack
    """

    __tablename__ = "ofa_infra_stack"

    id: Mapped[int] = mapped_column(primary_key=True)
    stack_name: Mapped[str] = mapped_column(String(20), unique=True)

    nodes: Mapped[List["Node"]] = relationship(back_populates="stack")

    def __repr__(self):
        return self.stack_name

    @hybrid_property
    def manager(self):
        """ Returns swarm manager of the stack """
        if not self.nodes:
            return None
        return self.nodes[0].manager

    def clear(self):
        """ Clear stack """
        db_session = Session.object_session(self)

        # remove all none-manager nodes
        manager = None
        for node in self.nodes:
            if node.node_name == 'manager':
                manager = node
                continue
            try:
                db_session.delete(node)
                db_session.commit()
            except OFAException as err:
                db_session.rollback()
                user_notify.info(err)

        # remove manager node
        if manager:
            try:
                db_session.delete(manager)
                db_session.commit()
            except OFAException as err:
                db_session.rollback()
                user_notify.info(err)

        user_notify.success(f"Cleared stack '{self.stack_name}' successfully")


@event.listens_for(InfraStack, 'before_delete')
def infrastack_before_delete(mapper, connection, target):
    """
    Checks if stack can be removed
    """
    if target.nodes:
        raise OFAException(f"Cannot remove stack '{target.stack_name}': non-empty nodes are part of it")
