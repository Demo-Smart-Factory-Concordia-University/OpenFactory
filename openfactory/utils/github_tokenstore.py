""" GitHub Token Store Module for OpenFactory. """

import os
import json
from openfactory.exceptions import OFAException
from typing import Dict


class GitHubTokenStore:
    """
    Class to manage GitHub access tokens.

    Provides methods to securely store, retrieve, and manage
    GitHub access tokens for different repositories.
    The tokens are stored in a JSON file in the user's home directory
    under the `.openfactory` directory.
    """

    def __init__(self):
        """ Initialize the token store. """
        self.config_dir = os.path.expanduser("~/.openfactory")
        self.token_file = os.path.join(self.config_dir, "github_tokens.json")
        self._ensure_secure_storage()

    def _ensure_secure_storage(self):
        os.makedirs(self.config_dir, exist_ok=True)
        os.chmod(self.config_dir, 0o700)
        if not os.path.exists(self.token_file):
            with open(self.token_file, "w") as f:
                json.dump({}, f)
            os.chmod(self.token_file, 0o600)

    def load_tokens(self) -> Dict:
        """
        Load tokens from the secure storage.

        Returns:
            dict: Dictionary of tokens.

        Raises:
            OFAException: If there is an error in decoding the token file.
        """
        try:
            with open(self.token_file, "r") as f:
                return json.load(f)
        except json.decoder.JSONDecodeError as err:
            raise OFAException(f"Error in decoding 'github access tokens': {err}")

    def save_tokens(self, tokens: Dict) -> None:
        """
        Save tokens to the secure storage.

        Args:
            tokens (dict): Dictionary of tokens to save.
        """
        with open(self.token_file, "w") as f:
            json.dump(tokens, f, indent=2)
        os.chmod(self.token_file, 0o600)

    def add_token(self, repo: str, user: str, token: str) -> None:
        """
        Add a new token for a specific repository.

        Args:
            repo (str): Repository name.
            user (str): Username associated with the token.
            token (str): The access token.
        """
        tokens = self.load_tokens()
        tokens[repo] = {"user": user, "token": token}
        self.save_tokens(tokens)

    def get_token(self, repo: str) -> Dict:
        """
        Get a token for a specific repository.

        Args:
            repo (str): Repository name.

        Returns:
            dict: Dictionary containing user and token.
        """
        tokens = self.load_tokens()
        return tokens.get(repo, None)

    def list_tokens(self):
        """ List all stored tokens. """
        tokens = self.load_tokens()
        return tokens
