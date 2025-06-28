from unittest import TestCase
from unittest.mock import MagicMock, patch, call
import pandas as pd
from openfactory.kafka import KafkaAssetConsumer
from openfactory.assets import Asset
from openfactory.assets.asset_base import BaseAsset


@patch("openfactory.assets.asset_base.AssetProducer")
class TestAsset(TestCase):
    """
    Test class Asset
    """

    def test_inherits_from_baseasset(self, MockAssetProducer):
        """ Test AssetUNS derives from BaseAsset """
        self.assertTrue(issubclass(Asset, BaseAsset))

    def test_init_sets_attributes(self, MockAssetProducer):
        """ Test correct inital attributes """
        asset = Asset('test_uns_001', ksqlClient=MagicMock(), bootstrap_servers='mocked_broker')
        self.assertEqual(asset.KSQL_ASSET_TABLE, 'assets')
        self.assertEqual(asset.KSQL_ASSET_ID, 'asset_uuid')
        self.assertEqual(asset.ASSET_CONSUMER_CLASS, KafkaAssetConsumer)
        self.assertEqual(asset.ASSET_ID, 'test_uns_001')

    def test_asset_uuid_returns_value(self, MockAssetProducer):
        """ Test asset_uuid returns correct value """
        asset = Asset("uuid-123", ksqlClient=MagicMock(), bootstrap_servers="mock_broker")

        # Ensure correct attributes
        self.assertEqual(asset.asset_uuid, "uuid-123")

    def test_get_reference_list_returns_uuids(self, MockAssetProducer):
        """ Test _get_reference_list returns list of UUIDs """
        mock_df = pd.DataFrame({'VALUE': ['ref_001, ref_002']})
        mock_ksqlClient = MagicMock()
        mock_ksqlClient.query.side_effect = [mock_df]

        asset = Asset('test_001', ksqlClient=mock_ksqlClient, bootstrap_servers='mocked_broker')
        result = asset._get_reference_list('above')

        self.assertEqual(result, ['ref_001', 'ref_002'])
        expected_query = "SELECT VALUE FROM assets WHERE key='test_001|references_above';"
        self.assertIn(call(expected_query), mock_ksqlClient.query.call_args_list)

    def test_get_reference_list_returns_empty_on_empty_df(self, MockAssetProducer):
        """ Test _get_reference_list returns empty list on empty query """
        mock_ksqlClient = MagicMock()
        mock_ksqlClient.query.side_effect = [pd.DataFrame()]

        asset = Asset('test_001', ksqlClient=mock_ksqlClient, bootstrap_servers='mocked_broker')
        result = asset._get_reference_list('below')
        self.assertEqual(result, [])

    def test_get_reference_list_returns_empty_on_blank_value(self, MockAssetProducer):
        """ Test _get_reference_list returns empty list on blank VALUE """
        mock_df = pd.DataFrame({'VALUE': ['   ']})
        mock_ksqlClient = MagicMock()
        mock_ksqlClient.query.side_effect = [mock_df]

        asset = Asset('test_001', ksqlClient=mock_ksqlClient, bootstrap_servers='mocked_broker')
        result = asset._get_reference_list('above')
        self.assertEqual(result, [])

    @patch('openfactory.assets.asset_class.Asset')
    def test_get_reference_list_returns_assets(self, MockAsset, MockAssetProducer):
        """ Test _get_reference_list returns Asset instances when as_assets=True """
        mock_df = pd.DataFrame({'VALUE': ['asset_010, asset_020']})
        mock_ksqlClient = MagicMock()
        mock_ksqlClient.query.side_effect = [mock_df]

        # Setup return values for mocked AssetUNS constructor
        mock_asset_1 = MagicMock()
        mock_asset_2 = MagicMock()
        MockAsset.side_effect = [mock_asset_1, mock_asset_2]

        asset = Asset('test_001', ksqlClient=mock_ksqlClient, bootstrap_servers='mocked_broker')
        result = asset._get_reference_list('below', as_assets=True)

        self.assertEqual(result, [mock_asset_1, mock_asset_2])
        MockAsset.assert_any_call(asset_uuid='asset_010', ksqlClient=mock_ksqlClient)
        MockAsset.assert_any_call(asset_uuid='asset_020', ksqlClient=mock_ksqlClient)
        self.assertEqual(MockAsset.call_count, 2)
