import os
import sys
import unittest

# Add project root to sys.path
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
result = test_runner.run(test_suite)

# Exit with non-zero code if any test failed
sys.exit(not result.wasSuccessful())
