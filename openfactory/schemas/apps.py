from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Optional
from openfactory.config import load_yaml
from openfactory.models.user_notifications import user_notify


class OpenFactoryApp(BaseModel):
    uuid: str = Field(..., description="Unique identifier for the app")
    image: str = Field(..., description="Docker image for the app")
    environment: Optional[List[str]] = Field(
        default=None, description="List of environment variables"
    )


class OpenFactoryAppsConfig(BaseModel):
    apps: Dict[str, OpenFactoryApp] = Field(
        ..., description="Dictionary of OpenFactory applications"
    )


def get_apps_from_config_file(apps_yaml_config_file):
    """
    Loads and validates OpenFactory applications configuration from a YAML file
    Returns dictionary of apps configurations or None in case of errors
    Side effect: sends user notifications in case of validation errors
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
