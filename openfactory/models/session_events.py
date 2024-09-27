from sqlalchemy import event
from sqlalchemy.orm import Session

from .user_notifications import user_notify
from .agents import Agent
from .nodes import Node


@event.listens_for(Session, 'persistent_to_deleted')
def receive_persistent_to_deleted(session, instance):
    """
    Sends user notifications when objects are deleted
    """
    if isinstance(instance, Agent):
        user_notify.success(f"Agent {instance.uuid} removed successfully")
    if isinstance(instance, Node):
        user_notify.success(f"Node '{instance.node_name}' removed successfully")
