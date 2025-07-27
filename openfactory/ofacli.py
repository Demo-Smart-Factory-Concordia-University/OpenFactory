"""
OpenFactory Command Line Interface.

Usage: ofa [OPTIONS] COMMAND [ARGS]...
Help: ofa --help


Becomes available after installing OpenFactory (after cloning the repository locally) like

> pip install .

or (during development)

> pip install -e .
"""

import sys
import paramiko.ssh_exception
from openfactory.ofa.cli import cli
from openfactory.models.user_notifications import user_notify
from openfactory.docker.docker_access_layer import dal
from openfactory.ofa.ksqldb import ksql
from openfactory.kafka.ksql import KSQLDBClientException
import openfactory.config as Config


def init_environment() -> bool:
    """ Setup OpenFactory environment (Docker, ksqlDB, notifications). """
    user_notify.setup(
        success_msg=lambda msg: print(f"{Config.OFA_SUCCSESS}{msg}{Config.OFA_END}"),
        fail_msg=lambda msg: print(f"{Config.OFA_FAIL}{msg}{Config.OFA_END}"),
        info_msg=print,
        warning_msg=lambda msg: print(f"{Config.OFA_WARNING}{msg}{Config.OFA_END}")
    )

    try:
        dal.connect()
    except (paramiko.ssh_exception.AuthenticationException,
            paramiko.ssh_exception.NoValidConnectionsError) as e:
        user_notify.fail(f"Connection to {Config.OPENFACTORY_MANAGER_NODE_DOCKER_URL} failed: {e}")
        return False

    try:
        ksql.connect(Config.KSQLDB_URL)
    except KSQLDBClientException:
        user_notify.fail('Failed to connect to ksqlDB server')
        return False

    return True


def main():
    """ Command line interface of OpenFactory. """
    skip_env_commands = {"--help", "version", "config"}
    if len(sys.argv) == 1 or sys.argv[1] in skip_env_commands:
        cli()
        return

    if not init_environment():
        exit(1)

    cli()


if __name__ == '__main__':
    main()
