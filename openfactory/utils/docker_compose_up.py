import subprocess
from openfactory.exceptions import DockerComposeException


def docker_compose_up(host, compose_file, compose_project_name=None):
    """ Spins up a Docker compose project """
    if compose_project_name:
        p = subprocess.Popen(f"docker --host {host} compose --file {compose_file} --project-name {compose_project_name} up --detach",
                             shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        p = subprocess.Popen(f"docker --host {host} compose --file {compose_file} up --detach",
                             shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ret = p.communicate()
    if p.returncode != 0:
        raise DockerComposeException(ret[1].decode('utf8'))
    return ret[1].decode('utf8')
