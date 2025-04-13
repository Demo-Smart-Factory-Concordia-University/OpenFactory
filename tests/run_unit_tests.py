import os
import unittest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Discover and run tests inside the tests/openfactory folder
test_loader = unittest.defaultTestLoader
test_suite = test_loader.discover(
    start_dir='tests/openfactory',
    pattern='test_*.py',
    top_level_dir=project_root
)

# Run the tests
test_runner = unittest.TextTestRunner(verbosity=2)
test_runner.run(test_suite)
