import docker
import yaml

import config.config as config


def down(yaml_config_file):
    """ Tear down OpenFactory infrastructure """

    # Load yaml description file
    with open(yaml_config_file, 'r') as stream:
        infra = yaml.safe_load(stream)

    for node, host in infra['nodes'].items():
        print("Removing", node)
        rem_client = docker.DockerClient(base_url="ssh://" + config.OPENFACTORY_USER + "@" + host)
        rem_client.swarm.leave()
        rem_client.close()

    print("Removing manager")
    client = docker.DockerClient(base_url="ssh://" + config.OPENFACTORY_USER + "@" + infra['manager'])
    client.swarm.leave(force=True)

    client.close()
