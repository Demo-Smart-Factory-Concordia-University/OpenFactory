from openfactory.openfactory import OpenFactory
from openfactory.openfactory_manager import OpenFactoryManager
from importlib.metadata import version


try:
    __version__ = version('openfactory')
except Exception:
    __version__ = "unknown"
