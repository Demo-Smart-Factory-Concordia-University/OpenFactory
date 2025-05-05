""" OpenFactory package. """
import os
from openfactory.openfactory import OpenFactory
from openfactory.openfactory_manager import OpenFactoryManager
from importlib.metadata import version


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


try:
    __version__ = version('openfactory')
except Exception:
    __version__ = "unknown"
