import docker
import openfactory.config as config
from openfactory.utils import load_yaml
from openfactory.models.user_notifications import user_notify
from openfactory.docker.docker_access_layer import dal


def remove_workers(workers, node_ip_map):
    """ Remove worker nodes """
    for name, details in workers.items():
        try:
            ip = details['ip']
            if ip not in node_ip_map:
                continue

            # drain the node
            user_notify.info(f'Draining node {name} ...')
            node = dal.docker_client.nodes.get(node_ip_map.get(ip))
            node_spec = node.attrs['Spec']
            node_spec['Availability'] = 'drain'
            node.update(node_spec)

            # leave swarm on worker node
            user_notify.info(f'Removing node {name} from cluster ...')
            docker_url = f"ssh://{config.OPENFACTORY_USER}@{ip}"
            node_client = docker.DockerClient(base_url=docker_url)
            node_client.swarm.leave()

            # remove node on OpenFactory Manger Node
            dal.docker_client.api.remove_node(node_ip_map.get(ip), force=True)
            user_notify.success(f'Removed node {name}')

        except (docker.errors.APIError) as err:
            user_notify.fail(f'Node "{name}" could not be removed. Error was:<br>"{err}"')


def remove_infrastack(stack_config_file):
    """
    Tear down an infrastructure stack based on a config file
    """
    # Load yaml description file
    stack = load_yaml(stack_config_file)

    # map nodes by IP
    node_ip_map = {
        node.attrs['Status']['Addr']: node.id for node in dal.docker_client.nodes.list()
        }

    remove_workers(stack['nodes']['workers'], node_ip_map)
