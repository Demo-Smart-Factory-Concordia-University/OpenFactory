from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, WriteOnlyMapped
from sqlalchemy.orm import relationship
from flask import current_app
from flask_login import UserMixin

from openfactory.datafabric.app import db
from openfactory.datafabric.app.main.models.tasks import RQTask
from openfactory.datafabric.app.main.models.notifications import Notification


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

    tasks: WriteOnlyMapped['RQTask'] = relationship(back_populates='user')
    notifications: WriteOnlyMapped['Notification'] = relationship(back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return self.username

    def submit_RQ_task(self, name, description, *args, **kwargs):
        """ Submmits an RQ task to the task queue """
        rq_job = current_app.task_queue.enqueue(f'openfactory.datafabric.app.main.rq_tasks.{name}',
                                                *args, **kwargs)
        task = RQTask(id=rq_job.get_id(),
                      name=name,
                      description=description,
                      user=self)
        db.session.add(task)
        db.session.commit()
        return task

    def get_RQ_tasks_in_progress(self):
        """ Returns all in progress RQ tasks of a user """
        query = self.tasks.select().where(RQTask.complete == 0)
        return db.session.scalars(query)

    def get_RQ_task_in_progress(self, name):
        query = self.tasks.select().where(RQTask.name == name,
                                          RQTask.complete == 0)
        return db.session.scalar(query)
