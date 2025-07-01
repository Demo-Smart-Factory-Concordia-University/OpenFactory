import unittest
from pydantic import ValidationError
from typing import List, Dict
from openfactory.schemas.uns import NamespaceItem, UNSSchemaModel, ConstraintType


class TestUNSSchemaModel(unittest.TestCase):
    """
    Unit tests for the UNSSchemaModel validation logic.
    """

    def make_namespace(self, keys_and_values: Dict[str, ConstraintType]) -> List[NamespaceItem]:
        """
        Helper to create a namespace structure from a dict of {key: value}
        """
        return [NamespaceItem({k: v}) for k, v in keys_and_values.items()]

    def test_valid_schema(self):
        """ Test a valid schema with correct template and structure """
        ns = self.make_namespace({'inc': 'ANY', 'area': 'ANY', 'station': 'ANY', 'attribute': 'ANY'})
        schema = UNSSchemaModel(namespace_structure=ns, uns_template='inc/area/station/attribute')
        self.assertEqual(schema.uns_template, 'inc/area/station/attribute')

    def test_missing_separator(self):
        """ Test template with no separator (no non-word character) """
        ns = self.make_namespace({'inc': 'ANY', 'attribute': 'ANY'})
        with self.assertRaises(ValidationError) as context:
            UNSSchemaModel(namespace_structure=ns, uns_template='incattribute')  # no separator
        self.assertIn("Could not determine separator", str(context.exception))

    def test_template_not_ending_in_attribute(self):
        """ Test template that does not end in 'attribute' """
        ns = self.make_namespace({'inc': 'ANY', 'station': 'ANY'})
        with self.assertRaises(ValidationError) as context:
            UNSSchemaModel(namespace_structure=ns, uns_template='inc.station')  # missing attribute
        self.assertIn("uns_template must end with 'attribute'", str(context.exception))

    def test_template_with_undefined_fields(self):
        """ Test template referencing fields not in namespace_structure """
        ns = self.make_namespace({'inc': 'ANY', 'station': 'ANY', 'attribute': 'ANY'})
        with self.assertRaises(ValidationError) as context:
            UNSSchemaModel(namespace_structure=ns, uns_template='inc.area.station.attribute')  # 'area' not defined
        self.assertIn("not defined in namespace_structure", str(context.exception))

    def test_template_with_wrong_field_order(self):
        """ Test template fields not matching order in namespace_structure """
        ns = self.make_namespace({'inc': 'ANY', 'area': 'ANY', 'station': 'ANY', 'attribute': 'ANY'})
        with self.assertRaises(ValidationError) as context:
            UNSSchemaModel(namespace_structure=ns, uns_template='inc/station/area/attribute')  # wrong order
        self.assertIn("not in the same order", str(context.exception))
