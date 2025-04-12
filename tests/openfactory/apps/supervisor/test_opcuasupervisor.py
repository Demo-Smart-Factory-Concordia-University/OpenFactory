import unittest
from unittest.mock import MagicMock, patch
from openfactory.apps.supervisor import OPCUASupervisor


class OPCUASupervisorTestCase(unittest.TestCase):
    """
    Tests for OPCUASupervisor class
    """

    def setUp(self):
        self.ksql_mock = MagicMock()

        # Patch AssetProducer
        self.asset_producer_patcher = patch("openfactory.assets.asset_class.AssetProducer")
        self.MockAssetProducer = self.asset_producer_patcher.start()
        self.addCleanup(self.asset_producer_patcher.stop)

        # Patch add_attribute
        patcher = patch.object(OPCUASupervisor, 'add_attribute')
        self.mock_add_attribute = patcher.start()
        self.addCleanup(patcher.stop)

    def test_constructor_adds_opcua_attributes(self):
        """ Test if OPCUASupervisor sets its OPC UA attributes correctly """

        OPCUASupervisor(
            supervisor_uuid='sup-opc-1',
            device_uuid='dev-opc-1',
            adapter_ip='192.168.0.10',
            adapter_port=4840,
            ksqlClient=self.ksql_mock,
            bootstrap_servers='mock_bootstrap'
        )

        calls = self.mock_add_attribute.call_args_list

        expected_ids = {
            'adapter_uri': {'value': 'opc.tcp://192.168.0.10:4840', 'type': 'Events', 'tag': 'AdapterURI'},
            'adapter_connection_status': {'value': 'UNAVAILABLE', 'type': 'Events', 'tag': 'ConnectionStatus'},
            'opcua_namespace_uri': {'value': 'demofactory', 'type': 'Events', 'tag': 'OPCUANamespaceURI'},
            'opcua_browseName': {'value': 'PROVER3018', 'type': 'Events', 'tag': 'OPCUABrowsName'},
        }

        # Check that all expected attribute IDs are in the call list
        actual_ids = [call.kwargs['attribute_id'] for call in calls]
        for expected_id in expected_ids:
            self.assertIn(expected_id, actual_ids, f"Missing attribute_id: {expected_id}")

        # Check that attribute values/types/tags match expectations
        for call in calls:
            attr_id = call.kwargs['attribute_id']
            asset_attr = call.kwargs['asset_attribute']
            if attr_id in expected_ids:
                expected = expected_ids[attr_id]
                self.assertEqual(asset_attr.value, expected['value'], f"Incorrect value for {attr_id}")
                self.assertEqual(asset_attr.type, expected['type'], f"Incorrect type for {attr_id}")
                self.assertEqual(asset_attr.tag, expected['tag'], f"Incorrect tag for {attr_id}")

    def test_opcua_client_initialized(self):
        """ Test if OPC UA client is initialized with correct URL """
        supervisor = OPCUASupervisor(
            supervisor_uuid='sup-opc-2',
            device_uuid='dev-opc-2',
            adapter_ip='10.0.0.42',
            adapter_port=4841,
            ksqlClient=self.ksql_mock,
            bootstrap_servers='mock_bootstrap'
        )

        expected_url = "opc.tcp://10.0.0.42:4841"
        actual_url = supervisor.opcua_client.server_url.geturl()

        self.assertEqual(expected_url, actual_url, "OPC UA client URL mismatch")

    def test_reconnect_interval_constant(self):
        """ Ensure the reconnect interval is set as expected """
        self.assertEqual(OPCUASupervisor.RECONNECT_INTERVAL, 10, "Reconnect interval constant mismatch")
