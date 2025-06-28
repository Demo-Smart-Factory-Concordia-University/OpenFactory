import unittest
from unittest.mock import MagicMock, patch, call
import pandas as pd
from openfactory.assets import AssetUNS
from openfactory.assets.asset_base import BaseAsset
from openfactory.kafka import KafkaAssetUNSConsumer


@patch("openfactory.assets.asset_base.AssetProducer")
class TestAssetUNS(unittest.TestCase):
    """
    Test class AssetUNS
    """

    def test_inherits_from_baseasset(self, MockAssetProducer):
        """ Test AssetUNS derives from BaseAsset """
        self.assertTrue(issubclass(AssetUNS, BaseAsset))

    def test_init_sets_attributes(self, MockAssetProducer):
        """ Test correct inital attributes """
        asset = AssetUNS('test_uns_001', ksqlClient=MagicMock(), bootstrap_servers='mocked_broker')
        self.assertEqual(asset.KSQL_ASSET_TABLE, 'assets_uns')
        self.assertEqual(asset.KSQL_ASSET_ID, 'uns_id')
        self.assertEqual(asset.ASSET_CONSUMER_CLASS, KafkaAssetUNSConsumer)
        self.assertEqual(asset.ASSET_ID, 'test_uns_001')

    def test_asset_uuid_returns_value(self, MockAssetProducer):
        """ Test asset_uuid returns correct value """
        # Setup mock DataFrame with expected data
        mock_df = pd.DataFrame({'ASSET_UUID': ['uuid-123']})
        mock_ksqlClient = MagicMock()
        mock_ksqlClient.query.return_value = mock_df

        asset = AssetUNS('test_uns_001', ksqlClient=mock_ksqlClient, bootstrap_servers='mocked_broker')
        result = asset.asset_uuid

        expected_query = (
            "SELECT asset_uuid FROM asset_to_uns_map WHERE uns_id='test_uns_001';"
        )
        self.assertIn(call(expected_query), mock_ksqlClient.query.call_args_list)
        self.assertEqual(result, 'uuid-123')

    def test_asset_uuid_returns_none_on_empty_df(self, MockAssetProducer):
        """ Test asset_uuid is None when no mapping """
        mock_ksqlClient = MagicMock()
        mock_ksqlClient.query.return_value = pd.DataFrame()
        asset = AssetUNS('test_uns_001', ksqlClient=mock_ksqlClient, bootstrap_servers='mocked_broker')

        result = asset.asset_uuid
        self.assertIsNone(result)

    def test_get_reference_list_returns_uuids(self, MockAssetProducer):
        """ Test _get_reference_list returns list of UUIDs """
        mock_map = pd.DataFrame({'ASSET_UUID': ['uuid-123']})
        mock_df = pd.DataFrame({'VALUE': ['ref_001, ref_002']})
        mock_ksqlClient = MagicMock()
        mock_ksqlClient.query.side_effect = [mock_map, mock_df]

        asset = AssetUNS('test_uns_001', ksqlClient=mock_ksqlClient, bootstrap_servers='mocked_broker')
        result = asset._get_reference_list('above')

        self.assertEqual(result, ['ref_001', 'ref_002'])
        expected_query = "SELECT VALUE FROM assets_uns WHERE key='test_uns_001|references_above';"
        self.assertIn(call(expected_query), mock_ksqlClient.query.call_args_list)

    def test_get_reference_list_returns_empty_on_empty_df(self, MockAssetProducer):
        """ Test _get_reference_list returns empty list on empty query """
        mock_map = pd.DataFrame({'ASSET_UUID': ['uuid-123']})
        mock_ksqlClient = MagicMock()
        mock_ksqlClient.query.side_effect = [mock_map, pd.DataFrame()]

        asset = AssetUNS('test_uns_001', ksqlClient=mock_ksqlClient, bootstrap_servers='mocked_broker')
        result = asset._get_reference_list('below')
        self.assertEqual(result, [])

    def test_get_reference_list_returns_empty_on_blank_value(self, MockAssetProducer):
        """ Test _get_reference_list returns empty list on blank VALUE """
        mock_map = pd.DataFrame({'ASSET_UUID': ['uuid-123']})
        mock_df = pd.DataFrame({'VALUE': ['   ']})
        mock_ksqlClient = MagicMock()
        mock_ksqlClient.query.side_effect = [mock_map, mock_df]

        asset = AssetUNS('test_uns_001', ksqlClient=mock_ksqlClient, bootstrap_servers='mocked_broker')
        result = asset._get_reference_list('above')
        self.assertEqual(result, [])

    @patch('openfactory.assets.asset_uns_class.AssetUNS')
    def test_get_reference_list_returns_assets(self, MockAssetUNS, MockAssetProducer):
        """ Test _get_reference_list returns AssetUNS instances when as_assets=True """
        mock_map = pd.DataFrame({'ASSET_UUID': ['uuid-123']})
        mock_df = pd.DataFrame({'VALUE': ['uns_010, uns_020']})
        mock_ksqlClient = MagicMock()
        mock_ksqlClient.query.side_effect = [mock_map, mock_df]

        # Setup return values for mocked AssetUNS constructor
        mock_asset_1 = MagicMock()
        mock_asset_2 = MagicMock()
        MockAssetUNS.side_effect = [mock_asset_1, mock_asset_2]

        asset = AssetUNS('test_uns_001', ksqlClient=mock_ksqlClient, bootstrap_servers='mocked_broker')
        result = asset._get_reference_list('below', as_assets=True)

        self.assertEqual(result, [mock_asset_1, mock_asset_2])
        MockAssetUNS.assert_any_call('uns_010', ksqlClient=mock_ksqlClient)
        MockAssetUNS.assert_any_call('uns_020', ksqlClient=mock_ksqlClient)
        self.assertEqual(MockAssetUNS.call_count, 2)
