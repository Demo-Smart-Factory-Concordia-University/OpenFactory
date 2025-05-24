import unittest
from unittest.mock import patch, MagicMock
from openfactory.openfactory_deploy_strategy import SwarmDeploymentStrategy, LocalDockerDeploymentStrategy


class TestSwarmDeploymentStrategy(unittest.TestCase):
    """
    Unit tests for class SwarmDeploymentStrategy
    """

    @patch("openfactory.openfactory_deploy_strategy.dal.docker_client")
    def test_swarm_deploy(self, mock_docker_client):
        """ Test Docker Swarm deploy method """
        mock_create = MagicMock()
        mock_docker_client.services.create = mock_create
        strategy = SwarmDeploymentStrategy()
        strategy.deploy(
            image="test-image",
            name="test-service",
            env=["ENV=prod"],
            labels={"role": "web"},
            command="run",
            ports={8080: 80},
            networks=["net1"],
            constraints=["node.role==manager"],
            resources={"Limits": {"NanoCPUs": 500000000}},
            mode={"Replicated": {"Replicas": 2}}
        )

        mock_create.assert_called_once()
        args, kwargs = mock_create.call_args
        self.assertEqual(kwargs["image"], "test-image")
        self.assertEqual(kwargs["name"], "test-service")
        self.assertEqual(kwargs["env"], ["ENV=prod"])
        self.assertEqual(kwargs["labels"], {"role": "web"})
        self.assertEqual(kwargs["command"], "run")
        self.assertIsNotNone(kwargs["endpoint_spec"])
        self.assertEqual(kwargs["networks"], ["net1"])
        self.assertEqual(kwargs["constraints"], ["node.role==manager"])
        self.assertEqual(kwargs["resources"]["Limits"]["NanoCPUs"], 500000000)
        self.assertEqual(kwargs["mode"], {"Replicated": {"Replicas": 2}})


class TestLocalDockerDeploymentStrategy(unittest.TestCase):
    """
    Unit tests for class LocalDockerDeploymentStrategy
    """

    @patch("openfactory.openfactory_deploy_strategy.docker.from_env")
    def test_local_deploy(self, mock_from_env):
        """ Test local Docker deploy method using direct docker.from_env() """
        mock_docker_client = MagicMock()
        mock_run = MagicMock()
        mock_docker_client.containers.run = mock_run
        mock_from_env.return_value = mock_docker_client

        strategy = LocalDockerDeploymentStrategy()
        strategy.deploy(
            image="test-image",
            name="test-container",
            env=["ENV=dev"],
            labels={"type": "api"},
            command="start",
            ports={8080: 80},
            networks=["bridge"],
            resources={"Limits": {"NanoCPUs": 1000000000}}
        )

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertEqual(kwargs["image"], "test-image")
        self.assertEqual(kwargs["name"], "test-container")
        self.assertEqual(kwargs["environment"], ["ENV=dev"])
        self.assertEqual(kwargs["command"], "start")
        self.assertTrue(kwargs["detach"])
        self.assertEqual(kwargs["ports"], {"80/tcp": 8080})
        self.assertEqual(kwargs["network"], "bridge")
        self.assertEqual(kwargs["labels"], {"type": "api"})
        self.assertEqual(kwargs["nano_cpus"], 1000000000)
