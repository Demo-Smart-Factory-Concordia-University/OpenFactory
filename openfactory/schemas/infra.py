""" Pydantic schemas for validating OpenFactory infrastructure configuration files. """

from typing import Dict, Optional
from pydantic import BaseModel, Field, RootModel, model_validator, ValidationError
from ipaddress import IPv4Address
from openfactory.models.user_notifications import user_notify
from openfactory.config import load_yaml


class Volume(BaseModel):
    """ Volume Schema. """
    driver_opts: Optional[Dict[str, str]]


class Volumes(RootModel[Dict[str, Optional[Volume]]]):
    """ Volumes Schema. """
    pass


class Node(BaseModel):
    """ Docker Swarm Node Schema. """
    ip: IPv4Address
    labels: Optional[Dict[str, str]] = None


class Managers(RootModel[Dict[str, Node]]):
    """ Docker Swarm Managers Schema. """
    pass


class Workers(RootModel[Dict[str, Node]]):
    """ Docker Swarm Workers Schema. """
    pass


class Nodes(BaseModel):
    """ Docker Swarm Nodes Schema. """
    managers: Optional[Dict[str, Node]] = None
    workers: Optional[Dict[str, Node]] = None

    @model_validator(mode='after')
    def check_unique_ips(cls, values: Dict) -> Dict:
        """
        Validates that IP addresses are unique across managers and workers.

        Args:
            values (Dict): Dictionary of values to validate.

        Returns:
            Dict: Validated values.

        Raises:
            ValueError: If IP addresses are not unique.
        """
        ips = []

        # Collect IP addresses from managers
        if values.managers:  # Access 'managers' directly as an attribute
            ips += [node.ip for node in values.managers.values()]

        # Collect IP addresses from workers
        if values.workers:  # Access 'workers' directly as an attribute
            ips += [node.ip for node in values.workers.values()]

        # Check if all IPs are unique
        if len(ips) != len(set(ips)):
            raise ValueError("IP addresses must be unique across managers and workers.")

        return values


class IPAMConfig(BaseModel):
    """ IPAM Configuration Schema. """
    subnet: str  # Subnet in CIDR format
    gateway: Optional[str] = None  # Optional gateway IP address
    ip_range: Optional[str] = Field(None, alias="ip_range")  # Optional IP range
    aux_addresses: Optional[Dict[str, str]] = Field(None, alias="aux_addresses")  # Optional auxiliary addresses


class IPAM(BaseModel):
    """ IPAM Schema. """
    config: list[IPAMConfig]


class Network(BaseModel):
    """ Network Schema. """
    name: Optional[str] = None
    ipam: IPAM


class Networks(BaseModel):
    """ Networks Schema. """
    openfactory_network: Network = Field(..., alias="openfactory-network")
    docker_ingress_network: Network = Field(..., alias="docker-ingress-network")


class InfrastructureSchema(BaseModel):
    """ Infrastructure Schema. """
    nodes: Nodes
    networks: Optional[Dict[str, Network]] = None
    volumes: Optional[Volumes] = None


def get_infrastructure_from_config_file(infra_yaml_config_file: str) -> Optional[Dict[str, InfrastructureSchema]]:
    """
    Load and validate infrastructure configuration from a YAML file.

    This function reads a YAML file containing infrastructure configuration,
    validates its content using the :class:`InfrastructureSchema` Pydantic model,
    and returns the parsed data as a dictionary.

    Args:
        infra_yaml_config_file (str): Path to the YAML file defining the infrastructure configuration.

    Returns:
        Optional[Dict[str, InfrastructureSchema]]: A dictionary of validated infrastructure configuration data,
                                                   or `None` if validation fails.

    Note:
        In case of validation errors, user notifications will be triggered and `None` will be returned.
    """
    # load yaml description file
    cfg = load_yaml(infra_yaml_config_file)

    # validate and create devices configuration
    try:
        infra = InfrastructureSchema(**cfg)
    except ValidationError as err:
        user_notify.fail(f"Provided YAML configuration file has invalid format\n{err}")
        return None
    except ValueError as err:
        user_notify.fail(f"Provided YAML configuration file has invalid format\n{err}")
        return None
    return infra.model_dump()
