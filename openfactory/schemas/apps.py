""" OpenFactory Application Schema. """

from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Optional
from openfactory.config import load_yaml
from openfactory.models.user_notifications import user_notify


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


def get_apps_from_config_file(apps_yaml_config_file: str) -> Optional[Dict[str, OpenFactoryApp]]:
    """
    Loads and validates OpenFactory applications configuration from a YAML file.

    Args:
        apps_yaml_config_file (str): Path to the YAML configuration file.

    Returns:
        dict: Dictionary of apps configurations or None in case of errors.

    Raises:
        ValidationError: If the provided YAML configuration file has an invalid format.
        ValueError: If the provided YAML configuration file has an invalid format.
    """
    # load yaml description file
    cfg = load_yaml(apps_yaml_config_file)

    # validate and create devices configuration
    try:
        apps_cfg = OpenFactoryAppsConfig(**cfg)
    except ValidationError as err:
        user_notify.fail(f"Provided YAML configuration file has invalid format\n{err}")
        return None
    except ValueError as err:
        user_notify.fail(f"Provided YAML configuration file has invalid format\n{err}")
        return None
    return apps_cfg.model_dump()['apps']
