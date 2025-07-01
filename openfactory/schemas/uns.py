""" OpenFactory Unified Namespace (UNS) Schema. """

import yaml
import re
from typing import List, Dict, Any, Union, Literal
from pydantic import BaseModel, RootModel, model_validator
from openfactory.utils.open_uris import open_ofa
import openfactory.config as config


# --- Internal models for validation ---

ConstraintType = Union[Literal["ANY"], str, List[str]]


class NamespaceItem(RootModel[Dict[str, ConstraintType]]):
    """
    Represents a single item in the OpenFactory namespace_structure.

    Each item is expected to be a dictionary with exactly one key,
    where the key is the level name (e.g., 'inc', 'area') and the value
    is the constraint for that level (e.g., a string, list of strings, or 'ANY').
    """

    @model_validator(mode="after")
    def check_one_key(self) -> "NamespaceItem":
        """
        Validates that the item has exactly one key.

        Returns:
            NamespaceItem: The validated instance.

        Raises:
            ValueError: If the dictionary does not contain exactly one key.
        """
        if len(self.root) != 1:
            raise ValueError(
                f"Each namespace_structure item must define exactly one key, got: {self.root}"
            )
        return self

    def key(self) -> str:
        """
        Returns the single key of the namespace item.

        Returns:
            str: The level name (e.g., 'inc', 'station').
        """
        return next(iter(self.root))

    def value(self) -> ConstraintType:
        """
        Returns the constraint value associated with the key.

        Returns:
            ConstraintType: The constraint (e.g., string, list of strings, or 'ANY').
        """
        return next(iter(self.root.values()))


class UNSSchemaModel(BaseModel):
    """
    Represents the schema definition for the OpenFactory Unified Namespace (UNS).

    Attributes:
        namespace_structure (List[NamespaceItem]): A list of namespace levels with their constraints.
        uns_template (str): A string template defining the path structure using level names
                            separated by a character (e.g., 'inc.area.station.asset.attribute').
    """

    namespace_structure: List[NamespaceItem]
    uns_template: str

    @model_validator(mode="after")
    def check_template_fields(self) -> "UNSSchemaModel":
        """
        Validates `uns_template`.

        Validates that the `uns_template`:
            - Contains a recognizable separator character.
            - Ends with the 'attribute' field.
            - References only fields defined in the `namespace_structure`.

        Returns:
            UNSSchemaModel: The validated instance.

        Raises:
            ValueError: If the separator cannot be determined.
            ValueError: If the template does not end with 'attribute'.
            ValueError: If the template references fields not defined in the namespace structure.
        """
        all_keys = [item.key() for item in self.namespace_structure]

        # Determine separator
        match = re.search(r"\W", self.uns_template)
        if not match:
            raise ValueError("Could not determine separator from uns_template")
        sep = match.group(0)

        # Extract fields from the template
        fields = self.uns_template.split(sep)

        # Validate ending
        if fields[-1] != "attribute":
            raise ValueError("uns_template must end with 'attribute'")

        # Validate all fields exist
        missing = [f for f in fields if f not in all_keys]
        if missing:
            raise ValueError(
                f"uns_template contains fields which are not defined in namespace_structure: {missing}"
            )

        # Validate order of fields
        expected_order = [key for key in all_keys if key in fields]
        if expected_order != fields:
            raise ValueError(
                f"uns_template fields are not in the same order as defined in namespace_structure. "
                f"Expected order: {expected_order}, got: {fields}"
            )

        return self


# --- Main public class for logic ---

class UNSSchema:
    """
    Represents and validates the Unified Namespace (UNS) schema.

    This class loads a schema definition from a YAML file, validates it with Pydantic,
    and provides methods to extract, validate, and generate UNS paths for OpenFactory assets.

    Attributes:
        separator (str): The character used to separate fields in the UNS template.
        template_fields (List[str]): The list of fields in the UNS template including 'attribute'.
        allowed_values (Dict[str, ConstraintType]): Mapping of UNS level names to their constraints.
    """

    def __init__(self, schema_yaml_file: str = config.OPENFACTORY_UNS_SCHEMA):
        """
        Initializes the UNS schema from a YAML file.

        Args:
            schema_yaml_file (str): UNS schema YAML file including path.

        Raises:
            pydantic.ValidationError: If the schema fails Pydantic validation.
        """
        with open_ofa(schema_yaml_file) as f:
            raw = yaml.safe_load(f)

        # Validate using Pydantic model
        model = UNSSchemaModel(**raw)

        # Template fields and separator
        self.separator = re.search(r"\W", model.uns_template).group(0)
        self.template_fields = model.uns_template.split(self.separator)

        # Build constraints from validated structure
        self.allowed_values: Dict[str, ConstraintType] = {
            item.key(): item.value() for item in model.namespace_structure
        }

    def extract_uns_fields(self, asset_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts all UNS hierarchy fields for an asset, based on the template and schema.

        This includes:
        - Constant fields (e.g., "inc": "OpenFactory") defined in the schema.
          If the asset defines them with a different value, an error is raised.
        - Constrained fields (e.g., from an enum list or "ANY") that are expected from the asset dictionary.
        - Excludes the final "attribute" field from the UNS path.
        - If the "asset" field is not provided explicitly, it is populated from the "uuid" field of the asset.

        Args:
            asset_dict (Dict[str, Any]): The dictionary representing a single asset configuration.

        Returns:
            Dict[str, Any]: A dictionary mapping each field (excluding "attribute") to its resolved value,
                            combining schema-defined constants and asset-provided values.

        Raises:
            ValueError: If a constant field is overridden incorrectly,
                        if a constraint is malformed,
                        or if "asset" is missing and "uuid" is not defined.
        """
        result = {}
        for field in self.template_fields:
            if field == "attribute":
                continue

            constraint = self.allowed_values.get(field)

            if isinstance(constraint, str) and constraint != "ANY":
                if field in asset_dict and asset_dict[field] != constraint:
                    raise ValueError(
                        f"Field '{field}' is constant and must be '{constraint}', but asset config has '{asset_dict[field]}'"
                    )
                result[field] = constraint
            elif constraint == "ANY":
                if field in asset_dict:
                    result[field] = asset_dict[field]
            elif isinstance(constraint, list):
                if field in asset_dict:
                    result[field] = asset_dict[field]
            else:
                raise ValueError(f"Unexpected constraint for field '{field}': {constraint}")

        if "asset" not in result:
            if "uuid" not in asset_dict:
                raise ValueError("Asset 'uuid' must be defined in the Asset dictionary configuration.")
            result["asset"] = asset_dict["uuid"]

        return result

    def validate_uns_fields(self, asset_name: str, fields: Dict[str, Any]):
        """
        Validates UNS fields in the asset configuration.

        Validates that:
        - Asset fields form a contiguous prefix (no gaps) of the UNS template (excluding constant fields and 'attribute')
        - The last asset-provided field is 'asset'
        - Field values match allowed constraints

        Constant fields are validated during extraction and are not checked here.

        Args:
            asset_name (str): Asset identifier (used only for error reporting).
            fields (Dict[str, Any]): UNS-relevant fields extracted from asset config (with `extract_uns_fields`).

        Raises:
            ValueError: If fields are missing, incorrectly ordered, or values are invalid.
        """
        constant_fields = [k for k, v in self.allowed_values.items() if isinstance(v, str) and v != "ANY"]
        expected_device_fields = [f for f in self.template_fields if f != "attribute" and f not in constant_fields]
        provided_fields = list(fields.keys())

        # Remove constant fields from provided_fields for prefix check
        provided_device_fields = [f for f in provided_fields if f not in constant_fields]

        if not provided_device_fields:
            raise ValueError(
                f"Asset '{asset_name}': no UNS provided."
            )

        if provided_device_fields[-1] != "asset":
            raise ValueError(
                f"Asset '{asset_name}': last UNS field must be 'asset', got '{provided_device_fields[-1]}'"
            )

        # Remove 'asset' from both for prefix comparison
        expected_prefix = expected_device_fields[:-1]
        provided_prefix = provided_device_fields[:-1]

        # Check if provided_prefix is a contiguous prefix of expected_prefix
        if len(provided_prefix) > len(expected_prefix) or any(
            p != e for p, e in zip(provided_prefix, expected_prefix)
        ):
            raise ValueError(
                f"Asset '{asset_name}': fields {provided_device_fields} must form a contiguous prefix of the UNS template fields {expected_device_fields}"
            )

        # Value validation for all fields (including constants)
        for field in provided_fields:
            constraint = self.allowed_values.get(field)
            value = fields[field]

            if constraint == "ANY":
                continue
            elif isinstance(constraint, list):
                if value not in constraint:
                    raise ValueError(
                        f"Asset '{asset_name}': invalid value '{value}' for '{field}'. Allowed: {constraint}"
                    )

    def generate_uns_path(self, fields: Dict[str, Any]) -> str:
        """
        Generates the UNS path string by joining the hierarchy fields with the template separator.

        Args:
            fields (Dict[str, Any]): The validated UNS hierarchy fields.

        Returns:
            str: The generated UNS path string without the 'attribute' field.
        """
        parts = []

        for field in self.template_fields:
            if field == "attribute" or field not in fields:
                continue
            parts.append(str(fields[field]))

        return self.separator.join(parts)
