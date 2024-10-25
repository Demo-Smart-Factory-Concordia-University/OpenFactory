import unittest
import yaml
from pydantic import ValidationError
from openfactory.schemas.infra import InfrastructureSchema


class TestInfrastructureSchema(unittest.TestCase):
    """
    Unit tests for class InfrastructureSchema
    """

    def test_valid_infrastructure(self):
        """
        Test case for a valid OpenFactory infrastructure
        """
        yaml_data = """
                    nodes:
                        managers:
                            manager1:
                                ip: 123.100.7.100
                                labels:
                                    type: ofa
                            manager2:
                                ip: 123.100.7.200

                        workers:
                            node1:
                                ip: 123.100.7.101
                                labels:
                                    type: ofa
                            node2:
                                ip: 123.100.7.102

                    networks:
                        openfactory-network:
                            ipam:
                                config:
                                    - subnet: 10.0.2.0/24
                                      gateway: 10.0.2.1

                        docker-ingress-network:
                            name: ofa_ingress
                            ipam:
                                config:
                                    - subnet: 10.0.1.0/24

                    volumes:
                        vol1:

                        vol2:
                            driver_opts:
                                type: "nfs"
                                o: "addr= 123.100.7.567,rw"
                                device: ":/nfs/data/ofa"
                    """
        parsed_data = yaml.safe_load(yaml_data)
        InfrastructureSchema(**parsed_data)

        # only managers
        yaml_data = """
                    nodes:
                        managers:
                            manager1:
                                ip: 123.100.7.100
                                labels:
                                    type: ofa
                            manager2:
                                ip: 123.100.7.200
                    """
        parsed_data = yaml.safe_load(yaml_data)
        InfrastructureSchema(**parsed_data)

        # only workers
        yaml_data = """
                    nodes:
                        workers:
                            node1:
                                ip: 123.100.7.101
                                labels:
                                    type: ofa
                            node2:
                                ip: 123.100.7.102
                    """
        parsed_data = yaml.safe_load(yaml_data)
        InfrastructureSchema(**parsed_data)

    def test_invalid_ip_address(self):
        """
        Test case for an invalid IP address
        """
        yaml_data = """
                    nodes:
                        workers:
                            node1:
                                ip: 123.400.7.101
                    """
        parsed_data = yaml.safe_load(yaml_data)

        # Check error raised
        with self.assertRaises(ValidationError) as context:
            InfrastructureSchema(**parsed_data)

        # Check that the error message contains information about the invalid IP
        self.assertTrue("Input is not a valid IPv4 address" in str(context.exception))

    def test_none_unique_ip_address(self):
        """
        Test case for none-unique IP address
        """
        yaml_data = """
                    nodes:
                        managers:
                            manager1:
                                ip: 123.100.7.101
                        workers:
                            node1:
                                ip: 123.100.7.101
                    """
        parsed_data = yaml.safe_load(yaml_data)

        # Check error raised
        with self.assertRaises(ValidationError) as context:
            InfrastructureSchema(**parsed_data)

        # Check that the error message contains information about the none unique IP
        self.assertTrue("IP addresses must be unique" in str(context.exception))