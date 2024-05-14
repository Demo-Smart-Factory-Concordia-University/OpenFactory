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
        uri = 'github://somerepo:from_user@/some/path'
        open_ofa(uri)
        mock_open_github.assert_called_with(uri,
                                            'somerepo:from_user@/some/path')

    @patch("builtins.open")
    def test_open_ofa_local_fs(self, mock_open):
        """
        Test if 'open' is called for a local file system uri
        """
        uri = '/some/path'
        open_ofa(uri)
        mock_open.assert_called_with(uri)

    @patch("fsspec.open")
    @patch("openfactory.utils.open_uris.get_configuration")
    def test_open_github_no_tokens(self, mock_get_configuration, mock_fsspec_open):
        """
        Test if public repo download is attempted when no tokens are defined
        """
        mock_get_configuration.return_value = None
        uri = 'github://somerepo:from_user@/some/path'
        path = 'somerepo:from_user@/some/path'
        open_github(uri, path)
        mock_fsspec_open.assert_called_with(uri, 'r')

    @patch("fsspec.open")
    @patch("openfactory.utils.open_uris.get_configuration")
    def test_open_github_tokens(self, mock_get_configuration, mock_fsspec_open):
        """
        Test if tokens are extracted based on repo
        """
        tokens = '{"somerepo:myuser": {"token": "some_token", "user": "boss"}}'
        mock_get_configuration.return_value = tokens
        uri = 'github://somerepo:myuser@/some/path'
        path = 'somerepo:myuser@/some/path'
        open_github(uri, path)
        mock_fsspec_open.assert_called_with(uri,
                                            'r',
                                            username='boss',
                                            token='some_token')

    @patch("fsspec.open")
    @patch("openfactory.utils.open_uris.get_configuration")
    def test_open_github_no_token_for_repo(self, mock_get_configuration, mock_fsspec_open):
        """
        Test if public repo download is attempted when no token is defined for repo
        """
        tokens = '{"somerepo:myuser": {"token": "some_token", "user": "boss"}}'
        mock_get_configuration.return_value = tokens
        uri = 'github://some-other-repo:myuser@/some/path'
        path = 'some-other-repo:myuser@/some/path'
        open_github(uri, path)
        mock_fsspec_open.assert_called_with(uri, 'r',)

    @patch("fsspec.open")
    @patch("openfactory.utils.open_uris.get_configuration")
    def test_open_github_user_missconfigured(self, mock_get_configuration, *args):
        """
        Test if error raised if user missconfigured in tokens
        """
        tokens = '{"somerepo:myuser": {"token": "some_token"}}'
        mock_get_configuration.return_value = tokens
        uri = 'github://somerepo:myuser@/some/path'
        path = 'somerepo:myuser@/some/path'
        self.assertRaises(OFAException, open_github, uri, path)

    @patch("fsspec.open")
    @patch("openfactory.utils.open_uris.get_configuration")
    def test_open_github_token_missing(self, mock_get_configuration, *args):
        """
        Test if error raised if repo token missing in tokens
        """
        tokens = '{"somerepo:myuser": {"user": "boss"}}'
        mock_get_configuration.return_value = tokens
        uri = 'github://somerepo:myuser@/some/path'
        path = 'somerepo:myuser@/some/path'
        self.assertRaises(OFAException, open_github, uri, path)

    @patch("fsspec.open")
    @patch("openfactory.utils.open_uris.get_configuration")
    def test_open_github_token_missconfigured(self, mock_get_configuration, *args):
        """
        Test if error raised if repo token missconfigured in tokens
        """
        tokens = '{"somerepo:myuser": {"token": "some_token" "user": "boss"} }'
        mock_get_configuration.return_value = tokens
        uri = 'github://somerepo:myuser@/some/path'
        path = 'somerepo:myuser@/some/path'
        self.assertRaises(OFAException, open_github, uri, path)

    @patch("fsspec.open")
    @patch("openfactory.utils.open_uris.get_configuration")
    def test_open_github_download_error(self, mock_get_configuration, mock_fsspec_open):
        """
        Test if error raised if file can not be fetched
        """
        tokens = '{"somerepo:myuser": {"token": "some_token", "user": "boss"} }'
        mock_get_configuration.return_value = tokens
        mock_fsspec_open.side_effect = FileNotFoundError()
        uri = 'github://somerepo:myuser@/some/path'
        path = 'somerepo:myuser@/some/path'
        self.assertRaises(OFAException, open_github, uri, path)

    @patch("fsspec.open")
    @patch("openfactory.utils.open_uris.get_configuration")
    def test_open_github_permission_denied(self, mock_get_configuration, mock_fsspec_open):
        """
        Test if error raised if permission is denied
        """
        tokens = '{"somerepo:myuser": {"token": "some_token", "user": "boss"} }'
        mock_get_configuration.return_value = tokens
        mock_fsspec_open.side_effect = HTTPError()
        uri = 'github://somerepo:myuser@/some/path'
        path = 'somerepo:myuser@/some/path'
        self.assertRaises(OFAException, open_github, uri, path)

    @patch("fsspec.open")
    @patch("openfactory.utils.open_uris.get_configuration")
    def test_open_github_wrong_format_in_uri(self, mock_get_configuration, mock_fsspec_open):
        """
        Test if error raised if uri is misformatted
        """
        tokens = '{"somerepo:myuser": {"token": "some_token", "user": "boss"} }'
        mock_get_configuration.return_value = tokens
        mock_fsspec_open.side_effect = HTTPError()

        uri = 'github://somerepo/myuser/some/path'
        path = 'somerepo/myuser/some/path'
        self.assertRaises(OFAException, open_github, uri, path)

        uri = 'github://somerepo/myuser@/some/path'
        path = 'somerepo/myuser@/some/path'
        self.assertRaises(OFAException, open_github, uri, path)

        uri = 'github://somerepo:myuser/some/path'
        path = 'somerepo:myuser/some/path'
        self.assertRaises(OFAException, open_github, uri, path)
