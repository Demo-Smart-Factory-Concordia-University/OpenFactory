""" Event listeners for SQLAlchemy session lifecycle events. """

from sqlalchemy import event
from sqlalchemy.orm import Session

from openfactory.models.user_notifications import user_notify
from openfactory.models.agents import Agent


@event.listens_for(Session, 'persistent_to_deleted')
def receive_persistent_to_deleted(session: Session, instance: object) -> None:
    """
    Sends user notifications when objects are deleted.

    Args:
        session (Session): The SQLAlchemy session triggering the event.
        instance (object): The instance being deleted from the session.
    """
    if isinstance(instance, Agent):
        user_notify.success(f"Agent {instance.uuid} shut down successfully")
