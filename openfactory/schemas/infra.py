import yaml
from typing import Dict, Optional
from pydantic import BaseModel, Field, RootModel, model_validator, ValidationError
from ipaddress import IPv4Address
from openfactory.models.user_notifications import user_notify


class Volume(BaseModel):
    driver_opts: Optional[Dict[str, str]]


class Volumes(RootModel[Dict[str, Optional[Volume]]]):
    pass


class Node(BaseModel):
    ip: IPv4Address
    labels: Optional[Dict[str, str]] = None


class Managers(RootModel[Dict[str, Node]]):
    pass


class Workers(RootModel[Dict[str, Node]]):
    pass


class Nodes(BaseModel):
    managers: Optional[Dict[str, Node]] = None
    workers: Optional[Dict[str, Node]] = None

    @model_validator(mode='after')
    def check_unique_ips(cls, values):
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
    subnet: str  # Subnet in CIDR format
    gateway: Optional[str] = None  # Optional gateway IP address
    ip_range: Optional[str] = Field(None, alias="ip_range")  # Optional IP range
    aux_addresses: Optional[Dict[str, str]] = Field(None, alias="aux_addresses")  # Optional auxiliary addresses


class IPAM(BaseModel):
    config: list[IPAMConfig]


class Network(BaseModel):
    name: Optional[str] = None
    ipam: IPAM


class Networks(BaseModel):
    openfactory_network: Network = Field(..., alias="openfactory-network")
    docker_ingress_network: Network = Field(..., alias="docker-ingress-network")


class InfrastructureSchema(BaseModel):
    """
    Schema of OpenFactory infrastructure
    """
    nodes: Nodes
    networks: Optional[Dict[str, Network]] = None
    volumes: Optional[Volumes] = None


def get_infrastructure_from_config_file(infra_yaml_config_file):
    """
    Loads and validates infrastructure configuration from a YAML file
    Returns dictionary of infrastructure configuration or None in case of errors
    Side effect: sends user notifications in case of validation errors
    """
    # load yaml description file
    with open(infra_yaml_config_file, 'r') as stream:
        cfg = yaml.safe_load(stream)

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
