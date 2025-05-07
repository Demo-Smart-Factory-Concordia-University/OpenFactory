import os
import sys
import unittest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

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
