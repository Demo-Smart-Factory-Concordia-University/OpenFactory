""" Pydantic schemas for validating OpenFactory Application definitions. """

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
    Load, validate, and enrich OpenFactory application configurations from a YAML file using UNS metadata.

    This function reads a YAML file containing OpenFactory application definitions, validates its content
    using the :class:`OpenFactoryAppsConfig` Pydantic model, and augments each validated application entry
    with Unified Namespace (UNS) metadata derived from the provided schema.

    Args:
        apps_yaml_config_file (str): Path to the YAML file defining application configurations.
        uns_schema (UNSSchema): Schema instance used to extract and validate UNS metadata
                                for each application.

    Returns:
        Optional[Dict[str, OpenFactoryApp]]: A dictionary of validated and enriched application configurations,
                                             or `None` if validation fails.

    Note:
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
