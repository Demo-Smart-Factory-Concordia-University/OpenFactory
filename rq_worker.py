"""
DataFabric RQ worker
"""
from redis import Redis
from rq import Worker
from dotenv import load_dotenv
from openfactory.datafabric.config import Config


def rq_worker():
    # Preload libraries
    import openfactory.models    # noqa

    # Setup environment variables
    load_dotenv('.flaskenv')

    # Provide the worker with the list of queues to listen to
    w = Worker(['datafabric-tasks'], connection=Redis.from_url(Config.REDIS_URL))
    w.work()


if __name__ == "__main__":
    rq_worker()
