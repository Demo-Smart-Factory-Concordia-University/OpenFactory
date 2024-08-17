import docker
from openfactory.docker.docker_access_layer import dal


def swarm_manager():
    """
    Returns an active and reachable swarm manager or None
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
