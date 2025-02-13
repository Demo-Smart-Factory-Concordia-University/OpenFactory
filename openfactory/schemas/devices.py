from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from openfactory.models.user_notifications import user_notify
from openfactory.config import load_yaml
import openfactory.config as config


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

    @model_validator(mode='before')
    def validate_adapter(cls, values):
        ip = values.get('ip')
        image = values.get('image')
        # Either 'ip' or 'image' must be specified, but not both
        if (ip is None and image is None) or (ip and image):
            raise ValueError("Either 'ip' or 'image' must be specified in the adapter.")
        return values


class Agent(BaseModel):
    ip: str = None
    port: int
    device_xml: str = None
    adapter: Optional[Adapter] = None
    deploy: Optional[Deploy] = None

    @model_validator(mode='before')
    def validate_agent(cls, values):
        ip = values.get('ip')
        adapter = values.get('adapter')
        if ip is None:
            if values.get('device_xml') is None:
                raise ValueError("'device_xml' is missing")
            if adapter is None:
                raise ValueError("'adapter' definition is missing")
        else:
            if adapter:
                raise ValueError("'adapter' can not be defined for an external agent")
            if values.get('device_xml'):
                raise ValueError("'device_xml' can not be defined for an external agent")
        return values


class Supervisor(BaseModel):
    image: str
    adapter: Adapter
    deploy: Optional[Deploy] = None


class InfluxDB(BaseModel):
    url: str = None
    organisation: str = None
    token: str = None
    bucket: str = None

    def __init__(self, **kwargs):
        # Initialize the model with provided values
        super().__init__(**kwargs)

        # Handle the 'url' fallback logic
        if self.url is None:
            if not hasattr(config, 'INFLUXDB_URL') or config.INFLUXDB_URL is None:
                raise ValueError("Configuration error: 'url' is not provided, and 'INFLUXDB_URL' is not defined in openfactory.config")
            self.url = config.INFLUXDB_URL

        # Handle the 'token' fallback logic
        if self.token is None:
            if not hasattr(config, 'INFLUXDB_TOKEN') or config.INFLUXDB_TOKEN is None:
                raise ValueError("Configuration error: 'token' is not provided, and 'INFLUXDB_TOKEN' is not defined in openfactory.config")
            self.token = config.INFLUXDB_TOKEN


class Device(BaseModel):
    uuid: str
    agent: Agent
    supervisor: Optional[Supervisor] = None
    ksql_tables: Optional[List[str]] = None
    influxdb: Optional[InfluxDB] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.agent.deploy is None:
            # If deploy is not provided, create a default Deploy with replicas=1
            self.agent.deploy = Deploy(replicas=1)
        elif self.agent.deploy.replicas is None:
            # If deploy is provided but replicas is missing, set replicas to 1
            self.agent.deploy.replicas = 1

    @field_validator('ksql_tables', mode='before', check_fields=False)
    def validate_ksql_tables(cls, value):
        allowed_values = {'device', 'producer', 'agent'}
        if value:
            invalid_entries = set(value) - allowed_values
            if invalid_entries:
                raise ValueError(f"Invalid entries in ksql-tables: {invalid_entries}")
        return value


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
            if device_data['agent']['ip']:
                if device_data['agent']['device_xml']:
                    raise ValueError("'device_xml' can not be defined for an external agent")
                if device_data['agent']['adapter']:
                    raise ValueError("'adapter' can not be defined for an external agent")
                return
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
    cfg = load_yaml(devices_yaml_config_file)

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
