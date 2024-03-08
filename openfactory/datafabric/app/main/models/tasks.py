import redis
import rq
from typing import Optional
from sqlalchemy import String
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from openfactory.datafabric.app import db
from openfactory.datafabric.app.auth.models.users import User


class RQTask(db.Model):
    """
    RQ Task model
    """

    __tablename__ = 'rq_tasks'

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[Optional[str]] = mapped_column(String(80))
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id))
    user: Mapped[User] = relationship(back_populates='tasks')
    complete: Mapped[bool] = mapped_column(default=False)
