from unittest import TestCase
from unittest.mock import patch
from requests.exceptions import HTTPError
from openfactory.utils.open_uris import open_ofa
from openfactory.utils.open_uris import open_github
from openfactory.exceptions import OFAException


class test_open_uris(TestCase):
    """
    Unit tests for open_uris functions
    """

    @patch("openfactory.utils.open_uris.open_github")
    def test_open_ofa_github(self, mock_open_github):
        """
        Test if 'open_github' is called for a GitHub uri
        """
        uri = 'github://org:repo@/some/path'
        open_ofa(uri)
        mock_open_github.assert_called_with('org:repo@/some/path')

    @patch("builtins.open")
    def test_open_ofa_local_fs(self, mock_open):
        """
        Test if 'open' is called for a local file system uri
        """
        uri = '/some/path'
        open_ofa(uri)
        mock_open.assert_called_with(uri)

    @patch("fsspec.open")
    @patch("openfactory.utils.open_uris.GitHubTokenStore")
    def test_open_github_no_tokens(self, mock_token_store_class, mock_fsspec_open):
        """
        Test if public repo download is attempted when no tokens are defined
        """
        mock_token_store_instance = mock_token_store_class.return_value
        mock_token_store_instance.list_tokens.return_value = None
        uri = 'github://org:repo@/some/path'
        path = 'org:repo@/some/path'
        open_github(path)
        mock_fsspec_open.assert_called_with(uri, 'r')

    @patch("fsspec.open")
    @patch("openfactory.utils.open_uris.GitHubTokenStore")
    def test_open_github_tokens(self, mock_token_store_class, mock_fsspec_open):
        """
        Test if tokens are extracted based on repo
        """
        mock_token_store_instance = mock_token_store_class.return_value
        mock_token_store_instance.list_tokens.return_value = {"org:repo": {"token": "some_token", "user": "boss"}}
        uri = 'github://org:repo@/some/path'
        path = 'org:repo@/some/path'
        open_github(path)
        mock_fsspec_open.assert_called_with(uri,
                                            'r',
                                            username='boss',
                                            token='some_token')

    @patch("fsspec.open")
    @patch("openfactory.utils.open_uris.GitHubTokenStore")
    def test_open_github_no_token_for_repo(self, mock_token_store_class, mock_fsspec_open):
        """
        Test if public repo download is attempted when no token is defined for repo
        """
        mock_token_store_instance = mock_token_store_class.return_value
        mock_token_store_instance.list_tokens.return_value = {"org:repo": {"token": "some_token", "user": "boss"}}
        uri = 'github://org2:repo2@/some/path'
        path = 'org2:repo2@/some/path'
        open_github(path)
        mock_fsspec_open.assert_called_with(uri, 'r',)

    @patch("fsspec.open")
    @patch("openfactory.utils.open_uris.GitHubTokenStore")
    def test_open_github_user_missconfigured(self, mock_token_store_class, *args):
        """
        Test if error raised if user missconfigured in tokens
        """
        mock_token_store_instance = mock_token_store_class.return_value
        mock_token_store_instance.list_tokens.return_value = {"org:repo": {"token": "some_token"}}
        path = 'org:repo@/some/path'
        self.assertRaises(OFAException, open_github, path)

    @patch("fsspec.open")
    @patch("openfactory.utils.open_uris.GitHubTokenStore")
    def test_open_github_token_missing(self, mock_token_store_class, *args):
        """
        Test if error raised if repo token missing in tokens
        """
        mock_token_store_instance = mock_token_store_class.return_value
        mock_token_store_instance.list_tokens.return_value = {"org:repo": {"user": "boss"}}
        path = 'org:repo@/some/path'
        self.assertRaises(OFAException, open_github, path)

    @patch("fsspec.open")
    @patch("openfactory.utils.open_uris.GitHubTokenStore")
    def test_open_github_download_error(self, mock_token_store_class, mock_fsspec_open):
        """
        Test if error raised if file can not be fetched
        """
        mock_token_store_instance = mock_token_store_class.return_value
        mock_token_store_instance.list_tokens.return_value = {"org:repo": {"token": "some_token", "user": "boss"}}
        mock_fsspec_open.side_effect = FileNotFoundError()
        path = 'org:repo@/some/path'
        self.assertRaises(OFAException, open_github, path)

    @patch("fsspec.open")
    @patch("openfactory.utils.open_uris.GitHubTokenStore")
    def test_open_github_http_error(self, mock_token_store_class, mock_fsspec_open):
        """
        Test if OFAException raised if HTTPError
        """
        tokens = {"org:repo": {"token": "some_token", "user": "boss"}}
        mock_token_store_instance = mock_token_store_class.return_value
        mock_token_store_instance.list_tokens.return_value = tokens
        mock_fsspec_open.side_effect = HTTPError()

        path = 'org/repo/some/path'
        self.assertRaises(OFAException, open_github, path)
