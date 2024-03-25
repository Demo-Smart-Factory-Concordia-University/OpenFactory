"""
Mocks for Python Docker SDK objects
"""
from unittest.mock import Mock


""" Python Docker SDK Swarm object """
docker_swarm = Mock()
docker_swarm.attrs = {
    'JoinTokens': {'Worker': 'docker_swarm_manager_token'}
}
docker_swarm.init = Mock(return_value='swarm_node_id')
docker_swarm.leave = Mock()


""" Python Docker SDK Node object """
docker_node = Mock()
docker_node.attrs = {
    'Status': {'State': 'ready', 'Addr': '123.456.7.900'}
}


""" Python Docker SDK Nodes object """
docker_nodes = Mock()
docker_nodes.get = Mock(return_value=docker_node)


""" Python Docker SDK Networks object """
docker_networks = Mock()
docker_networks.create = Mock(return_value='docker_network')


""" return value of DockerClient.info() """
INFO_DIC = {
    'Swarm': {'NodeID': 'a node id'},
    'NCPU': 5,
    'MemTotal': 1073741824
}


""" Python Docker SDK Client object """
docker_client = Mock()
docker_client.info = Mock(return_value=INFO_DIC)
docker_client.nodes = docker_nodes
docker_client.networks = docker_networks
docker_client.swarm = docker_swarm
docker_client.close = Mock()


""" Python Docker SDK APIClient object """
docker_apiclient = Mock()
docker_apiclient.remove_node = Mock()
docker_apiclient.close = Mock()
