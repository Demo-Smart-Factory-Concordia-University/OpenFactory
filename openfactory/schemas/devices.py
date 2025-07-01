""" OpenFactory Adapter, Agent, Supervisor and Device Schema. """

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from openfactory.models.user_notifications import user_notify
from openfactory.config import load_yaml
import openfactory.config as config


class ResourcesDefinition(BaseModel):
    """ Resources Definition Schema. """
    cpus: float = None
    memory: str = None


class Resources(BaseModel):
    """ Resources Schema. """
    reservations: ResourcesDefinition = None
    limits: ResourcesDefinition = None


class Placement(BaseModel):
    """ Placement Schema. """
    constraints: List[str] = None


class Deploy(BaseModel):
    """ Deploy Schema. """
    replicas: Optional[int] = Field(default=1)
    resources: Resources = None
    placement: Placement = None


class Adapter(BaseModel):
    """ OpenFactory Adapter Schema. """
    ip: str = None
    image: str = None
    port: int
    environment: List[str] = None
    deploy: Optional[Deploy] = None

    @model_validator(mode='before')
    def validate_adapter(cls, values: Dict) -> Dict:
        """
        Validates the adapter configuration.

        Args:
            values (Dict): Dictionary of values to validate.

        Returns:
            Dict: Validated values.

        Raises:
            ValueError: If 'ip' or 'image' is missing or incorrectly defined.
        """
        ip = values.get('ip')
        image = values.get('image')
        # Either 'ip' or 'image' must be specified, but not both
        if (ip is None and image is None) or (ip and image):
            raise ValueError("Either 'ip' or 'image' must be specified in the adapter.")
        return values


class Agent(BaseModel):
    """ OpenFactory Agent Schema. """
    ip: str = None
    port: int
    device_xml: str = None
    adapter: Optional[Adapter] = None
    deploy: Optional[Deploy] = None

    @model_validator(mode='before')
    def validate_agent(cls, values: Dict) -> Dict:
        """
        Validates the agent configuration.

        Args:
            values (Dict): Dictionary of values to validate.

        Returns:
            Dict: Validated values.

        Raises:
            ValueError: If 'device_xml' or 'adapter' is missing or incorrectly defined.
        """
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
    """ OpenFactory Supervisor Schema. """
    image: str
    adapter: Adapter
    deploy: Optional[Deploy] = None


class InfluxDB(BaseModel):
    """ InfluxDB configuration. """
    url: str = None
    organisation: str = None
    token: str = None
    bucket: str = None

    def __init__(self, **kwargs: Dict):
        """
        Initialize the InfluxDB model.

        Args:
            **kwargs (Dict): Keyword arguments to initialize the model.

        Raises:
            ValueError: If 'url' or 'token' is not provided and not defined in the configuration.
        """
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
    """ OpenFactory Device Schema. """
    uuid: str
    agent: Agent
    supervisor: Optional[Supervisor] = None
    ksql_tables: Optional[List[str]] = None
    influxdb: Optional[InfluxDB] = None

    model_config = {
        "extra": "ignore"
    }

    def __init__(self, **data: Dict):
        """
        Initialize the Device model.

        Args:
            **data (Dict): Keyword arguments to initialize the model.
        """
        super().__init__(**data)
        if self.agent.deploy is None:
            # If deploy is not provided, create a default Deploy with replicas=1
            self.agent.deploy = Deploy(replicas=1)
        elif self.agent.deploy.replicas is None:
            # If deploy is provided but replicas is missing, set replicas to 1
            self.agent.deploy.replicas = 1

    @field_validator('ksql_tables', mode='before', check_fields=False)
    def validate_ksql_tables(cls, value: List[str]) -> List[str]:
        """
        Validates the ksql_tables field.

        Args:
            value (List[str]): List of ksql tables.

        Returns:
            List[str]: Validated list of ksql tables.

        Raises:
            ValueError: If the provided ksql tables contain invalid entries.
        """
        allowed_values = {'device', 'producer', 'agent'}
        if value:
            invalid_entries = set(value) - allowed_values
            if invalid_entries:
                raise ValueError(f"Invalid entries in ksql-tables: {invalid_entries}")
        return value


class DevicesConfig(BaseModel):
    """
    Schema for OpenFactory devices configurations in yaml files.

    Usage:
       devices = DevicesConfig(devices=yaml_data['devices'])
    or:
       devices = DevicesConfig(**yaml_data)

    Will raise an error if yaml_data does not follow the expected schema
    """

    devices: Dict[str, Device]

    def validate_devices(self) -> None:
        """
        Validates the devices configuration.

        Raises:
            ValueError: If the devices configuration is invalid.
        """
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
        """ Dictionary with all configured devices. """
        return self.model_dump()['devices']


def get_devices_from_config_file(devices_yaml_config_file: str) -> Optional[Dict[str, Device]]:
    """
    Loads and validates devices configuration from a YAML file.

    Args:
        devices_yaml_config_file (str): Path to the YAML configuration file

    Returns:
        dict: Dictionary of devices configurations or None in case of error

    Raises:
        ValidationError: If the provided YAML configuration file has an invalid format
        ValueError: If the provided YAML configuration file has an invalid format
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
