""" Fetch a Swarm manager. """

import docker
from openfactory.docker.docker_access_layer import dal
from typing import Optional


def swarm_manager() -> Optional[docker.models.nodes.Node]:
    """
    Returns an active and reachable Swarm manager node, or None if no such node is found.

    Attempts to list all nodes in the Docker Swarm and filters for manager nodes
    that are active, healthy, and reachable. If no active manager nodes are found, it returns None.

    Returns:
        Optional[docker.models.nodes.Node]: The first active and reachable manager node, or None if no such node exists.
    """
    client = dal.docker_client

    try:
        # List all nodes in the swarm
        nodes = client.nodes.list()

        # Filter manager nodes that are active and healthy
        active_healthy_managers = [
            node for node in nodes
            if node.attrs['Spec']['Role'] == 'manager' and
            node.attrs['Status']['State'] == 'ready' and
            node.attrs['ManagerStatus']['Reachability'] == 'reachable'
        ]

        # Check if we have any active and healthy manager nodes
        if not active_healthy_managers:
            print("No active and healthy manager nodes found.")
            return None

        # Return the first active and healthy manager node
        return active_healthy_managers[0]

    except docker.errors.APIError as e:
        print(f"An error occurred: {e}")
        return None
