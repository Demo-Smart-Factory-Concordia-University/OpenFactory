import unittest
import tempfile
import yaml
import os
from unittest import mock
from openfactory.schemas.uns import UNSSchema


class TestUNSSchema(unittest.TestCase):
    """
    Test class UNSSchema
    """

    def setUp(self):
        # Build a minimal valid schema and write to temp file
        self.schema_data = {
            "namespace_structure": [
                {"inc": "OpenFactory"},
                {"area": "A1"},
                {"workcenter": ["WC1", "WC2"]},
                {"station": ["S1", "S2"]},
                {"asset": "ANY"},
                {"attribute": "ANY"}
            ],
            "uns_template": "inc/area/workcenter/station/asset/attribute"
        }

        self.temp_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        yaml.dump(self.schema_data, self.temp_file)
        self.temp_file.close()

        self.schema = UNSSchema(schema_yaml_file=self.temp_file.name)

    def tearDown(self):
        os.remove(self.temp_file.name)

    def test_schema_model_validation_error_is_caught(self):
        """ Test that UNSSchema catches ValueError from UNSSchemaModel and re-raises it """
        with mock.patch("openfactory.schemas.uns.UNSSchemaModel", side_effect=ValueError("Mocked error")):
            with self.assertRaises(ValueError) as cm:
                UNSSchema(schema_yaml_file=self.temp_file.name)
            self.assertIn("Invalid UNS schema", str(cm.exception))
            self.assertIsInstance(cm.exception.__cause__, ValueError)

    def test_extract_uns_fields_valid(self):
        """ Test extract_uns_fields """
        asset = {"workcenter": "WC2", "station": "S1", "asset": "my_asset", "uuid": "device123"}
        result = self.schema.extract_uns_fields(asset)
        expected = {
            "inc": "OpenFactory",
            "area": "A1",
            "workcenter": "WC2",
            "station": "S1",
            "asset": "my_asset"
        }
        self.assertEqual(result, expected)

    def test_extract_uns_fields_invalid_constant(self):
        """ Test extract_uns_fields when a constant field is wrongly redefiend """
        asset = {"area": "WRONG", "workcenter": "WC2", "station": "S1", "uuid": "device123"}
        with self.assertRaises(ValueError) as cm:
            self.schema.extract_uns_fields(asset)
        self.assertIn("must be 'A1'", str(cm.exception))

    def test_extract_uns_fields_missing_asset(self):
        """ Test extract_uns_fields when not asset defined """
        asset = {"station": "S1", "uuid": "device123"}
        result = self.schema.extract_uns_fields(asset)
        expected = {
            "inc": "OpenFactory",
            "area": "A1",
            "station": "S1",
            "asset": "device123"
        }
        self.assertEqual(result, expected)

    def test_extract_uns_fields_missing_uuid(self):
        """ Test extract_uns_fields when not asset defined and asset UUID is missing """
        asset = {"station": "S1"}
        with self.assertRaises(ValueError) as cm:
            self.schema.extract_uns_fields(asset)
        self.assertIn("'uuid' must be defined", str(cm.exception))

    def test_validate_uns_fields_valid(self):
        """ Test validate_uns_fields """
        fields = {
            "inc": "OpenFactory",
            "area": "A1",
            "workcenter": "WC1",
            "station": "S2",
            "asset": "my-device"
        }
        self.schema.validate_uns_fields("my-device", fields)

    def test_validate_uns_fields_invalid_order(self):
        """ Test validate_uns_fields when none contiguous prefix """
        fields = {
            "inc": "OpenFactory",
            "area": "A1",
            "station": "S1",
            "asset": "my-device"
        }
        with self.assertRaises(ValueError) as cm:
            self.schema.validate_uns_fields("my-device", fields)
        self.assertIn("must form a contiguous prefix", str(cm.exception))

    def test_validate_uns_fields_invalid_value(self):
        """ Test validate_uns_fields with an invalid value for a field """
        fields = {
            "inc": "OpenFactory",
            "area": "A1",
            "workcenter": "WC2",
            "station": "S3",  # Invalid
            "asset": "my-device"
        }
        with self.assertRaises(ValueError) as cm:
            self.schema.validate_uns_fields("my-device", fields)
        self.assertIn("invalid value 'S3'", str(cm.exception))

    def test_validate_uns_fields_missing_asset(self):
        """ Test validate_uns_fields when asset missing """
        fields = {
            "inc": "OpenFactory",
            "area": "A1",
            "workcenter": "WC1",
            "station": "S2"
        }
        with self.assertRaises(ValueError) as cm:
            self.schema.validate_uns_fields("some-device", fields)
        self.assertIn("last UNS field must be 'asset'", str(cm.exception))

    def test_generate_uns_path(self):
        """ Test generate_uns_path """
        fields = {
            "inc": "OpenFactory",
            "area": "A1",
            "workcenter": "WC1",
            "station": "S2",
            "asset": "device123",
            "attribute": "temperature"
        }
        path = self.schema.generate_uns_path(fields)
        self.assertEqual(path, "OpenFactory/A1/WC1/S2/device123")
