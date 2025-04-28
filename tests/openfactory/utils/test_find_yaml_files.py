import os
import tempfile
import unittest
from openfactory.utils import find_yaml_files


class TestFindYamlFiles(unittest.TestCase):
    """
    Unit tests for the find_yaml_files function
    """

    def test_find_yaml_files_valid_directory(self):
        """ Test finding YAML files in a valid directory """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some YAML files matching the pattern
            file1 = os.path.join(temp_dir, 'app_test1.yml')
            file2 = os.path.join(temp_dir, 'app_test2.yml')
            with open(file1, 'w') as f:
                f.write('test: 1')
            with open(file2, 'w') as f:
                f.write('test: 2')

            # Create a non-matching file
            non_matching_file = os.path.join(temp_dir, 'not_app.yml')
            with open(non_matching_file, 'w') as f:
                f.write('test: 3')

            # Call the function
            result = find_yaml_files(temp_dir)

            # Assert that only matching files are returned
            self.assertEqual(len(result), 2)
            self.assertIn(file1, result)
            self.assertIn(file2, result)
            self.assertNotIn(non_matching_file, result)

    def test_find_yaml_files_invalid_directory(self):
        """ Test finding YAML files in an invalid directory """
        invalid_dir = '/non/existent/directory'
        with self.assertRaises(ValueError) as context:
            find_yaml_files(invalid_dir)
        self.assertEqual(str(context.exception), f"{invalid_dir} is not a valid directory.")

    def test_find_yaml_files_recursive_search(self):
        """ Test finding YAML files in a directory and its subdirectories """
        with tempfile.TemporaryDirectory() as temp_dir:
            sub_dir = os.path.join(temp_dir, 'subdir')
            os.makedirs(sub_dir)

            # Create YAML files in both directories
            file1 = os.path.join(temp_dir, 'app_test1.yml')
            file2 = os.path.join(sub_dir, 'app_test2.yml')
            with open(file1, 'w') as f:
                f.write('test: 1')
            with open(file2, 'w') as f:
                f.write('test: 2')

            # Call the function
            result = find_yaml_files(temp_dir)

            # Assert that files from both directories are returned
            self.assertEqual(len(result), 2)
            self.assertIn(file1, result)
            self.assertIn(file2, result)

    def test_find_yaml_files_no_matching_files(self):
        """ Test finding YAML files when no files match the pattern """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files that do not match the pattern
            file1 = os.path.join(temp_dir, 'not_app1.yml')
            file2 = os.path.join(temp_dir, 'not_app2.yml')
            with open(file1, 'w') as f:
                f.write('test: 1')
            with open(file2, 'w') as f:
                f.write('test: 2')

            # Call the function
            result = find_yaml_files(temp_dir)

            # Assert that no files are returned
            self.assertEqual(len(result), 0)

    def test_find_yaml_files_empty_directory(self):
        """ Test finding YAML files in an empty directory """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Call the function on an empty directory
            result = find_yaml_files(temp_dir)

            # Assert that no files are returned
            self.assertEqual(len(result), 0)

    def test_find_yaml_files_custom_pattern(self):
        """ Test finding YAML files with a custom pattern """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with a custom pattern
            file1 = os.path.join(temp_dir, 'custom_test1.yml')
            file2 = os.path.join(temp_dir, 'custom_test2.yml')
            with open(file1, 'w') as f:
                f.write('test: 1')
            with open(file2, 'w') as f:
                f.write('test: 2')

            # Call the function with a custom pattern
            result = find_yaml_files(temp_dir, pattern='custom_*.yml')

            # Assert that only files matching the custom pattern are returned
            self.assertEqual(len(result), 2)
            self.assertIn(file1, result)
            self.assertIn(file2, result)
