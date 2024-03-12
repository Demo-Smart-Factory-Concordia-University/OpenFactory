"""
OpenFactory exceptions
"""


class DockerComposeException(Exception):
    """ Docker compose returned an error """
    pass


class OFAConfigurationException(Exception):
    """ Something is misconfigured """
    pass
