"""
DataFabric RQ worker
"""
from redis import Redis
from rq import Worker
from dotenv import load_dotenv
from openfactory.models.user_notifications import user_notify
from openfactory.datafabric.config import Config


def rq_worker():

    # Setup user notifications
    user_notify.success = lambda msg: user_notify.user.send_notification(msg, "success")
    user_notify.info = lambda msg: user_notify.user.send_notification(msg, "info")
    user_notify.fail = lambda msg: user_notify.user.send_notification(msg, "danger")

    # Setup environment variables
    load_dotenv('.flaskenv')

    # Provide the worker with the list of queues to listen to
    w = Worker(['datafabric-tasks'], connection=Redis.from_url(Config.REDIS_URL))
    w.work()


if __name__ == "__main__":
    rq_worker()
