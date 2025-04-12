from sqlalchemy import event
from sqlalchemy.orm import Session

from openfactory.models.user_notifications import user_notify
from openfactory.models.agents import Agent


@event.listens_for(Session, 'persistent_to_deleted')
def receive_persistent_to_deleted(session, instance):
    """
    Sends user notifications when objects are deleted
    """
    if isinstance(instance, Agent):
        user_notify.success(f"Agent {instance.uuid} shut down successfully")
