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

import sys
import yaml
import docker
import docker.types
import openfactory.config as config


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


def init_infrastructure(networks):
    """ Initialize  infrastructure """

    # setup OPENFACTORY_MANAGER_NODE as the first swarm manager
    client = docker.from_env()
    client.swarm.init(advertise_addr=config.OPENFACTORY_MANAGER_NODE)

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

    # create the openfactory-network
    client.networks.create(
        name=config.OPENFACTORY_NETWORK,
        driver='overlay',
        attachable=True,
        ipam=ipam_config(networks['openfactory-network'])
    )


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python init_infrastructure.py <infrastructure_config_file>")
        sys.exit(1)

    with open(sys.argv[1], 'r') as stream:
        cfg = yaml.safe_load(stream)

    init_infrastructure(cfg['networks'])
