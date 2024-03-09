from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from openfactory.datafabric.app import db
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from openfactory.datafabric.app.auth.models.users import User


class Notification(db.Model):
    """
    Notification model
    """

    __tablename__ = 'user_notifications'

    id: Mapped[int] = mapped_column(primary_key=True)
    message: Mapped[str] = mapped_column(String(80))
    type: Mapped[str] = mapped_column(String(80))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    user: Mapped['User'] = relationship(back_populates='notifications')

    def __repr__(self):
        return f"{self.user.username}: {self.message}"
