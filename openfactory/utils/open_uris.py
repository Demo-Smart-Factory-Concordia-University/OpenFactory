""" Open files from different URIs using fsspec. """

import fsspec
from requests.exceptions import HTTPError
from openfactory.exceptions import OFAException
from openfactory.utils.github_tokenstore import GitHubTokenStore


def open_github(path: str) -> fsspec.core.OpenFile:
    """
    Open a file from GitHub.

    Args:
        path (str): Path to the file in the format 'repo:owner@/path/to/file'

    Returns:
        file object: Opened file object

    Raises:
        OFAException: If the file cannot be found or permission is denied.
    """
    uri = f"github://{path}"
    repo = path.split('@', 1)[0]
    tokenStore = GitHubTokenStore()
    tokens = tokenStore.list_tokens()

    # validate GitHub tokens
    if tokens:
        if repo in tokens:
            if 'user' not in tokens[repo]:
                raise OFAException(f"GitHub access token for '{repo}' missconfigured. No 'user' field defined")
            if 'token' not in tokens[repo]:
                raise OFAException(f"GitHub access token for '{repo}' missconfigured. No 'token' field defined")

    # download file from GitHub
    try:
        if tokens and repo in tokens:
            fs = fsspec.open(uri, 'r',
                             username=tokens[repo]['user'],
                             token=tokens[repo]['token'])
        else:
            fs = fsspec.open(uri, 'r')
        f = fs.open()
    except FileNotFoundError:
        raise OFAException(f"Could not download '{uri}'. File was not found")
    except HTTPError:
        raise OFAException(f"Could not download '{uri}'. Permission denied")
    except (TypeError, ValueError):
        raise OFAException(f"Could not interpret '{uri}'.\nCheck it follows the format 'github://repo:owner@/path'")

    return f


def open_ofa(uri) -> fsspec.core.OpenFile:
    """
    Open file based on URI using fsspec.

    Args:
        uri (str): URI of the file to open.

    Returns:
        file object: Opened file object.
    """
    protocol, path = fsspec.core.split_protocol(uri)

    match protocol:
        case 'github': return open_github(path)

    return open(uri)
