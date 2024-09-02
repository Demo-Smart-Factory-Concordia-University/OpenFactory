import click
from datetime import datetime, timezone
from openfactory.docker.docker_access_layer import dal


def print_services(node_id):
    """ Print information on services running on a node """
    services = dal.docker_client.services.list()
    formatted_lines = []
    for service in services:
        tasks = dal.docker_client.api.tasks(filters={"service": service.name})
        for task in tasks:
            if task['NodeID'] == node_id and task['Status']['State'] == 'running':
                ports = service.attrs.get('Endpoint', {}).get('Ports', [])
                public_ports = ', '.join([str(port['PublishedPort']) for port in ports if 'PublishedPort' in port])
                started_at_str = task['Status']['Timestamp']
                trimmed_timestamp = started_at_str[:26] + 'Z'
                started_at = datetime.strptime(trimmed_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                time_running = datetime.now(timezone.utc) - started_at
                hours, remainder = divmod(time_running.total_seconds(), 3600)
                minutes, _ = divmod(remainder, 60)
                running_for = f"{int(hours)}h {int(minutes)}m ago" if hours else f"{int(minutes)}m ago"
                formatted_lines.append(f"{service.name:25}  Running since {running_for:15} {public_ports}")

    for i, line in enumerate(formatted_lines):
        if i < len(formatted_lines) - 1:
            print(f"  ├ {line}")
        else:
            print(f"  └ {line}")


@click.command(name='ls')
@click.option('-v', '--verbose', 'verbose',
              flag_value='verbose', default=False,
              help='Increase verbosity')
def click_ls(verbose):
    """ List OpenFactory nodes """
    nodes = dal.docker_client.nodes.list()
    for node in nodes:
        cpus = node.attrs['Description']['Resources']['NanoCPUs'] / 1E9
        ram = node.attrs['Description']['Resources']['MemoryBytes'] / (1024 ** 3)
        node_type = 'Manager' if 'ManagerStatus' in node.attrs else 'Worker'
        print(f"{node.attrs['Description']['Hostname']} {node.attrs['Status']['Addr']} ({cpus} CPUs {ram:.1f} GB) {node_type:8} {node.attrs['Spec']['Availability']:8} {node.attrs['Status']['State']}")
        if verbose:
            print("  SERVICE                      CURRENT STATE                 PUBLIC PORTS")
            print_services(node.id)
            print()
