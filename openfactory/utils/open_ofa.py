import fsspec
import json
from requests.exceptions import HTTPError
from openfactory.exceptions import OFAException
from openfactory.models.configurations import get_configuration


def open_github(uri, path):
    """
    Open a file from GitHub
    """
    repo = path.split('@', 1)[0]
    tokens = get_configuration('github_access_tokens')

    # validate GitHub token
    if tokens:
        try:
            tokens = json.loads(tokens)
        except json.decoder.JSONDecodeError as err:
            raise OFAException(f"Error in decoding 'github_access_tokens': {err}")
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

    return f


def open_ofa(uri):
    """
    Open file based on URI using fsspec
    """
    protocol, path = fsspec.core.split_protocol(uri)

    match protocol:
        case 'github': return open_github(uri, path)

    return open(uri)
