"""
DataFabric RQ worker
"""
from redis import Redis
from rq import Worker
from dotenv import load_dotenv

# Preload libraries
import openfactory.models    # noqa

# Setup environmetn variables
load_dotenv('.flaskenv')

# Provide the worker with the list of queues (str) to listen to.
w = Worker(['datafabric-tasks'], connection=Redis())
w.work()
