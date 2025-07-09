""" OpenFactory Application Schema. """

from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Optional
from openfactory.config import load_yaml
from openfactory.models.user_notifications import user_notify
from openfactory.schemas.uns import UNSSchema


class OpenFactoryApp(BaseModel):
    """ OpenFactory Application Schema."""
    uuid: str = Field(..., description="Unique identifier for the app")
    image: str = Field(..., description="Docker image for the app")
    environment: Optional[List[str]] = Field(
        default=None, description="List of environment variables"
    )


class OpenFactoryAppsConfig(BaseModel):
    """ OpenFactory Applications Configuration Schema."""
    apps: Dict[str, OpenFactoryApp] = Field(
        ..., description="Dictionary of OpenFactory applications"
    )

    @property
    def apps_dict(self):
        """ Dictionary with all configured OpenFactory applications. """
        return self.model_dump()['apps']


def get_apps_from_config_file(apps_yaml_config_file: str, uns_schema: UNSSchema) -> Optional[Dict[str, OpenFactoryApp]]:
    """
    Load, validate, and enrich with UNS data OpenFactory application configurations from a YAML file.

    This function reads a YAML configuration file that defines a collection of OpenFactory applications,
    validates its structure using the `DevicesConfig` model, and augments each device
    entry with corresponding UNS (Unified Namespace) metadata extracted using the provided schema.

    Args:
        apps_yaml_config_file (str): Path to the YAML configuration file.
        uns_schema (UNSSchema): An instance of the UNS schema used to generate the UNS metadata

    Returns:
        dict: Dictionary of apps configurations or None in case of errors.

    Raises:
        ValidationError: If the provided YAML configuration file has an invalid format.
        ValueError: If the provided YAML configuration file has an invalid format.

    Notes:
        In case of validation errors, user notifications will be triggered and `None` will be returned.
    """
    # load yaml description file
    cfg = load_yaml(apps_yaml_config_file)

    # validate and create apps configuration
    try:
        apps_cfg = OpenFactoryAppsConfig(**cfg)
    except ValidationError as err:
        user_notify.fail(f"Provided YAML configuration file has invalid format\n{err}")
        return None
    except ValueError as err:
        user_notify.fail(f"Provided YAML configuration file has invalid format\n{err}")
        return None

    # inject UNS data into the validated apps configurations
    apps = apps_cfg.apps_dict
    for app_name, raw_app_data in cfg['apps'].items():
        uns_fields = uns_schema.extract_uns_fields(raw_app_data)
        uns_schema.validate_uns_fields(app_name, uns_fields)
        uns_id = uns_schema.generate_uns_path(uns_fields)

        apps[app_name]["uns"] = {
            "levels": uns_fields,
            "uns_id": uns_id,
        }
    return apps
