"""
Python script to initialize OpenFactory
Run this script on the OpenFactory Manager Node defined in
the entry OPENFACTORY_MANAGER_NODE of the OpenFactory
configuration file openfactory/config/openfactory.yml

It will
  - create an initial Docker Swarm manager on the machine where the script is run
  - create a Ingress network (replacing the standard one if needed)
  - create the OpenFactory Network

Usage:
   python init_infrastructure.py <infrastructure_config_file>

The infrastructure_config_file must contain the definition of the OpenFactory Network
and optionally the ingress network, in case the standard Docker Swarm ingress network has to be
replaced:

networks:
  openfactory-network:
    ipam:
      config:
        - subnet: 10.2.0.0/24
          gateway: 10.2.0.1
          ip_range: 10.2.0.128/25

  docker-ingress-network:
    name: ofa_ingress
    ipam:
      config:
        - subnet: 10.1.0.0/24
"""

import socket
import sys
import docker
import docker.types
import openfactory.config as config
from openfactory.schemas.infra import get_infrastructure_from_config_file


def get_manager_labels(data):
    """ get the name of the openfactory manager node """

    # Get IP address of host
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(('8.8.8.8', 80))
        ip_address = s.getsockname()[0]

    # Loop through managers to find the matching IP address
    for manager, details in data['nodes']['managers'].items():
        if details['ip'] == ip_address:
            labels = {'name': manager}
            if 'labels' in details:
                labels.update(details['labels'])
            return labels

    # Return 'ofa_manager' if the IP address is not found
    return {'name': 'ofa_manager'}


def ipam_config(network):
    """ get the IPAM configuration """
    ipam_pools = []
    if 'ipam' in network and 'config' in network['ipam']:
        for pool in network['ipam']['config']:
            ipam_pools.append(docker.types.IPAMPool(
                subnet=pool.get('subnet'),
                gateway=pool.get('gateway'),
                iprange=pool.get('ip_range')
            ))

    # Create the IPAM configuration
    ipam_config = docker.types.IPAMConfig(
        driver=network['ipam'].get('driver', 'default'),
        pool_configs=ipam_pools
    )
    return ipam_config


def create_volume(client, volume_name, driver_opts):
    """ create a docker volume """
    try:
        client.volumes.create(
            name=volume_name,
            driver="local",
            driver_opts=driver_opts
        )
        print(f"Volume '{volume_name}' created successfully")
    except docker.errors.APIError as e:
        print(f"Error creating volume: {e}")


def init_infrastructure(networks, manager_labels, volumes):
    """ Initialize  infrastructure """

    # setup OPENFACTORY_MANAGER_NODE as the first swarm manager
    client = docker.from_env()
    try:
        node_id = client.swarm.init(advertise_addr=config.OPENFACTORY_MANAGER_NODE)
    except docker.errors.APIError as err:
        print(f"Could not initalize the OpenFactory manager node on this machine\n{err}")
        exit(1)
    node = client.nodes.get(node_id)
    node_spec = node.attrs['Spec']
    node_spec['Labels'] = manager_labels
    node.update(node_spec)
    print("Initial node created successfully")

    # replace the ingress network if needed
    if 'docker-ingress-network' in networks:
        network = client.networks.get('ingress')
        network.remove()
        client.networks.create(
            name=networks['docker-ingress-network']['name'],
            driver='overlay',
            ingress=True,
            ipam=ipam_config(networks['docker-ingress-network'])
        )
        print("Docker ingress network created successfully")

    # create the openfactory-network
    client.networks.create(
        name=config.OPENFACTORY_NETWORK,
        driver='overlay',
        attachable=True,
        ipam=ipam_config(networks['openfactory-network'])
    )
    print(f"Network '{config.OPENFACTORY_NETWORK}' created successfully.")

    # create docker volumes
    if volumes:
        for volume_name, volume_config in volumes.items():
            if volume_config:
                driver_opts = volume_config.get('driver_opts', {})
            else:
                driver_opts = {}
            create_volume(client, volume_name, driver_opts)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python init_infrastructure.py <infrastructure_config_file>")
        sys.exit(1)

    cfg = get_infrastructure_from_config_file(sys.argv[1])

    if 'openfactory-network' not in cfg['networks']:
        print("Could not initialise the OpenFactory infrastructure.")
        print("The network 'openfactory-network' has to be defined.")
        exit(1)

    init_infrastructure(cfg['networks'], get_manager_labels(cfg), cfg.get('volumes', {}))
