import yaml
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ValidationError
from openfactory.models.user_notifications import user_notify


class RuntimeConfig(BaseModel):
    cpus: float = None


class Runtime(BaseModel):
    agent: RuntimeConfig = None
    producer: RuntimeConfig = None
    adapter: RuntimeConfig = None


class ResourcesDefinition(BaseModel):
    cpus: float = None
    memory: str = None


class Resources(BaseModel):
    reservations: ResourcesDefinition = None
    limits: ResourcesDefinition = None


class Placement(BaseModel):
    constraints: List[str] = None


class Deploy(BaseModel):
    replicas: Optional[int] = Field(default=1)
    resources: Resources = None
    placement: Placement = None


class Adapter(BaseModel):
    ip: str = None
    image: str = None
    port: int
    environment: List[str] = None
    deploy: Optional[Deploy] = None

    @classmethod
    def validate(cls, values):
        ip = values.get('ip')
        image = values.get('image')
        if (ip is None and image is None) or (ip and image):
            raise ValueError("Either 'ip' or 'image' must be specified in the adapter.")
        return values


class Agent(BaseModel):
    port: int
    device_xml: str
    adapter: Adapter
    deploy: Optional[Deploy] = None


class Device(BaseModel):
    uuid: str
    agent: Agent
    runtime: Runtime = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.agent.deploy is None:
            # If deploy is not provided, create a default Deploy with replicas=1
            self.agent.deploy = Deploy(replicas=1)
        elif self.agent.deploy.replicas is None:
            # If deploy is provided but replicas is missing, set replicas to 1
            self.agent.deploy.replicas = 1


class DevicesConfig(BaseModel):
    """
    Schema for OpenFactory devices configurations in yaml files

    Usage:
       devices = DevicesConfig(devices=yaml_data['devices'])
    or:
       devices = DevicesConfig(**yaml_data)

    Will raise an error if yaml_data does not follow the expected schema
    """

    devices: Dict[str, Device]

    def validate_devices(self):
        for device_name, device_data in self.devices_dict.items():
            adapter = device_data['agent']['adapter']
            ip = adapter.get('ip')
            image = adapter.get('image')
            if ip is None and image is None:
                raise ValueError(f"Either 'ip' or 'image' must be specified for the adapter of {device_name}.")
            if ip is not None and image is not None:
                raise ValueError(f"Only one of 'ip' or 'image' should be specified for the adapter of {device_name}.")

    @property
    def devices_dict(self):
        """ Dictionary with all configured devices """
        return self.model_dump()['devices']


def get_devices_from_config_file(devices_yaml_config_file):
    """
    Loads and validates devices configuration from a YAML file
    Returns dictionary of devices configurations or None in case of errors
    Side effect: sends user notifications in case of validation errors
    """
    # load yaml description file
    with open(devices_yaml_config_file, 'r') as stream:
        cfg = yaml.safe_load(stream)

    # validate and create devices configuration
    try:
        devices_cfg = DevicesConfig(**cfg)
        devices_cfg.validate_devices()
    except ValidationError as err:
        user_notify.fail(f"Provided YAML configuration file has invalid format\n{err}")
        return None
    except ValueError as err:
        user_notify.fail(f"Provided YAML configuration file has invalid format\n{err}")
        return None
    return devices_cfg.devices_dict
