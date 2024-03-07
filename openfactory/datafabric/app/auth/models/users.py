from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from flask_login import UserMixin

from openfactory.datafabric.app import db


class User(UserMixin, db.Model):
    """
    User model
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), index=True,
                                          unique=True)
    fullname: Mapped[str] = mapped_column(String(120), index=True,
                                          unique=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(256))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return self.username
