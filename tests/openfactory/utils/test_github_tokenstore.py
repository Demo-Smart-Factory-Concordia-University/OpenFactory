import os
import json
import unittest
from openfactory.exceptions import OFAException
from openfactory.utils.github_tokenstore import GitHubTokenStore


class TestGitHubTokenStore(unittest.TestCase):
    """
    Unit tests for the GitHubTokenStore class
    """
    def setUp(self):
        """ Set up a temporary directory and mock environment for testing """
        self.mock_config_dir = "/tmp/mock_openfactory"
        self.mock_token_file = os.path.join(self.mock_config_dir, "github_tokens.json")
        self.token_store = GitHubTokenStore()
        self.token_store.config_dir = self.mock_config_dir
        self.token_store.token_file = self.mock_token_file

        # Ensure the mock directory and file are clean before each test
        if os.path.exists(self.mock_config_dir):
            for root, dirs, files in os.walk(self.mock_config_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.mock_config_dir)

    def tearDown(self):
        """ Clean up the temporary directory after tests """
        if os.path.exists(self.mock_config_dir):
            for root, dirs, files in os.walk(self.mock_config_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.mock_config_dir)

    def test_ensure_secure_storage_creates_directory_and_file(self):
        """ Test that the secure storage directory and file are created """
        self.token_store._ensure_secure_storage()
        self.assertTrue(os.path.exists(self.mock_config_dir))
        self.assertTrue(os.path.exists(self.mock_token_file))
        self.assertEqual(oct(os.stat(self.mock_config_dir).st_mode)[-3:], "700")
        self.assertEqual(oct(os.stat(self.mock_token_file).st_mode)[-3:], "600")

    def test_load_tokens_returns_empty_dict_if_file_is_empty(self):
        """ Test that load_tokens returns an empty dictionary if the file is empty """
        self.token_store._ensure_secure_storage()
        tokens = self.token_store.load_tokens()
        self.assertEqual(tokens, {})

    def test_load_tokens_raises_exception_on_invalid_json(self):
        """ Test that load_tokens raises an exception if JSON file is invalid """
        self.token_store._ensure_secure_storage()
        # Write invalid JSON to the token file
        with open(self.mock_token_file, "w") as f:
            f.write("{invalid_json}")

        with self.assertRaises(OFAException) as context:
            self.token_store.load_tokens()
        self.assertIn("Error in decoding 'github access tokens'", str(context.exception))

    def test_save_tokens_writes_tokens_to_file(self):
        """ Test that save_tokens writes tokens to the file """
        self.token_store._ensure_secure_storage()
        tokens = {"repo1": {"user": "user1", "token": "token1"}}
        self.token_store.save_tokens(tokens)

        with open(self.mock_token_file, "r") as f:
            saved_tokens = json.load(f)
        self.assertEqual(saved_tokens, tokens)

    def test_add_token_saves_new_token(self):
        """ Test that add_token saves a new token to the file """
        self.token_store._ensure_secure_storage()
        self.token_store.add_token("repo1", "user1", "token1")

        tokens = self.token_store.load_tokens()
        self.assertIn("repo1", tokens)
        self.assertEqual(tokens["repo1"], {"user": "user1", "token": "token1"})

    def test_get_token_returns_correct_token(self):
        """ Test that get_token returns the correct token for a repository """
        self.token_store._ensure_secure_storage()
        self.token_store.add_token("repo1", "user1", "token1")

        token = self.token_store.get_token("repo1")
        self.assertEqual(token, {"user": "user1", "token": "token1"})

    def test_get_token_returns_none_for_nonexistent_repo(self):
        """ Test that get_token returns None for a nonexistent repository """
        self.token_store._ensure_secure_storage()
        token = self.token_store.get_token("nonexistent_repo")
        self.assertIsNone(token)

    def test_list_tokens_returns_all_tokens(self):
        """ Test that list_tokens returns all stored tokens """
        self.token_store._ensure_secure_storage()
        self.token_store.add_token("repo1", "user1", "token1")
        self.token_store.add_token("repo2", "user2", "token2")

        tokens = self.token_store.list_tokens()
        self.assertEqual(tokens, {
            "repo1": {"user": "user1", "token": "token1"},
            "repo2": {"user": "user2", "token": "token2"}
        })
