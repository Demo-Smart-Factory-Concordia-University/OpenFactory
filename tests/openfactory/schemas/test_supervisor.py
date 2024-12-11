import unittest
from pydantic import ValidationError
from openfactory.schemas.devices import Supervisor, Adapter, Deploy, Resources, ResourcesDefinition, Placement


class TestSupervisor(unittest.TestCase):
    """
    Unit tests for class Supervisor
    """

    def setUp(self):
        """ Set up test data """
        self.valid_adapter = Adapter(
            ip="192.168.1.1",
            port=8080,
            environment=["ENV_VAR=value"],
            deploy=Deploy(
                replicas=2,
                resources=Resources(
                    reservations=ResourcesDefinition(cpus=1.5, memory="512Mi"),
                    limits=ResourcesDefinition(cpus=2.0, memory="1Gi")
                ),
                placement=Placement(constraints=["node.role==worker"])
            )
        )

    def test_supervisor_with_valid_data(self):
        """ Test that Supervisor initializes correctly with valid data """
        supervisor = Supervisor(
            image="supervisor-image:latest",
            adapter=self.valid_adapter,
            deploy=Deploy(
                replicas=3,
                resources=Resources(
                    reservations=ResourcesDefinition(cpus=2.0, memory="1Gi"),
                    limits=ResourcesDefinition(cpus=3.0, memory="2Gi")
                ),
                placement=Placement(constraints=["node.role==manager"])
            )
        )
        self.assertEqual(supervisor.image, "supervisor-image:latest")
        self.assertEqual(supervisor.adapter.ip, "192.168.1.1")
        self.assertEqual(supervisor.deploy.replicas, 3)

    def test_supervisor_missing_image(self):
        """ Test that Supervisor raises an error when 'image' is missing """
        with self.assertRaises(ValidationError):
            Supervisor(
                adapter=self.valid_adapter
            )

    def test_supervisor_missing_adapter(self):
        """ Test that Supervisor raises an error when 'adapter' is missing """
        with self.assertRaises(ValidationError):
            Supervisor(
                image="supervisor-image:latest"
            )

    def test_supervisor_optional_deploy(self):
        """ Test that Supervisor initializes correctly without 'deploy' """
        supervisor = Supervisor(
            image="supervisor-image:latest",
            adapter=self.valid_adapter
        )
        self.assertIsNone(supervisor.deploy)


if __name__ == "__main__":
    unittest.main()
