from unittest import TestCase
from unittest.mock import patch
from openfactory.datafabric.config import Config
from rq_worker import rq_worker


@patch("rq_worker.load_dotenv")
@patch("rq_worker.Redis.from_url")
@patch("rq_worker.Worker")
class Test_rq_worker(TestCase):
    """
    Unit test of rq_worker
    """

    def test_load_dotenv(self, mock_worker, mock_redis, mock_load_dotenv):
        """
        Test if '.flaskenv' loaded
        """
        rq_worker()
        mock_load_dotenv.assert_called_once_with('.flaskenv')

    def test_redic_connection(self, mock_worker, mock_redis, *args):
        """
        Test setup of Redis connection
        """
        rq_worker()
        mock_redis.assert_called_once_with(Config.REDIS_URL)

    def test_rq_worker_queue(self, mock_worker, mock_redis, *args):
        """
        Test RQ Worker queue
        """
        rq_worker()
        self.assertEqual(mock_worker.call_args[0], (['datafabric-tasks'],))
