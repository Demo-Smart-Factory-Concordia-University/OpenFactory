import docker
import yaml

import config.config as config


def up(yaml_config_file):
    """ Setup OpenFactory infrastructure """

    # Load yaml description file
    with open(yaml_config_file, 'r') as stream:
        infra = yaml.safe_load(stream)

    client = docker.DockerClient(base_url="ssh://" + config.OPENFACTORY_USER + "@" + infra['manager'])
    client.swarm.init(advertise_addr=infra['manager'])
    token = client.swarm.attrs['JoinTokens']['Worker']

    # create overlay network
    print("Create network")
    client.networks.create(infra['network'],
                           driver='overlay',
                           attachable=True)

    # attach nodes to swarm cluster
    for node, host in infra['nodes'].items():
        print("Attaching ", node)
        rem_client = docker.DockerClient(base_url="ssh://" + config.OPENFACTORY_USER + "@" + host)
        rem_client.swarm.join([infra['manager']], join_token=token)
        rem_client.close()

    client.close()
