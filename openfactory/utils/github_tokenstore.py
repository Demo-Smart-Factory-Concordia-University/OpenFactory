import os
import json
from openfactory.exceptions import OFAException


class GitHubTokenStore:
    """
    Class to manage GitHub access tokens
    """
    def __init__(self):
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

    def load_tokens(self):
        """ Load tokens from the secure storage """
        try:
            with open(self.token_file, "r") as f:
                return json.load(f)
        except json.decoder.JSONDecodeError as err:
            raise OFAException(f"Error in decoding 'github access tokens': {err}")

    def save_tokens(self, tokens):
        """ Save tokens to the secure storage """
        with open(self.token_file, "w") as f:
            json.dump(tokens, f, indent=2)
        os.chmod(self.token_file, 0o600)

    def add_token(self, repo, user, token):
        """ Add a new token for a specific repository """
        tokens = self.load_tokens()
        tokens[repo] = {"user": user, "token": token}
        self.save_tokens(tokens)

    def get_token(self, repo):
        """ Get a token for a specific repository """
        tokens = self.load_tokens()
        return tokens.get(repo, None)

    def list_tokens(self):
        """ List all stored tokens """
        tokens = self.load_tokens()
        return tokens
