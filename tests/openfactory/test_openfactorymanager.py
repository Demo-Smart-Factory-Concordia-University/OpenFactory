import unittest
import docker
from unittest.mock import patch, MagicMock
from openfactory import OpenFactoryManager
from openfactory.exceptions import OFAException


class TestOpenFactoryManager(unittest.TestCase):
    """
    Tests for class OpenFactoryManager
    """

    @patch("openfactory.openfactory.KSQL")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("openfactory.openfactory_manager.config")
    @patch("openfactory.openfactory_manager.dal")
    @patch("openfactory.openfactory_manager.open_ofa")
    @patch("openfactory.openfactory_manager.user_notify")
    @patch("openfactory.openfactory_manager.register_asset")
    @patch("openfactory.openfactory_manager.Asset")
    def test_deploy_mtconnect_agent(self, MockAsset, mock_register_asset, mock_user_notify, mock_open_ofa, mock_dal, mock_config, mock_open, MockKSQL):
        """
        Test deploy_mtconnect_agent
        """

        # Mock config values
        mock_config.MTCONNECT_AGENT_CFG_FILE = "mock_agent_cfg_file"
        mock_config.MTCONNECT_AGENT_IMAGE = "mock_image"
        mock_config.OPENFACTORY_NETWORK = "mock_network"

        # Mock the content of the agent config file
        mock_open.return_value.__enter__.return_value.read.return_value = "mock agent configuration content"

        # Set up mocks
        mock_client = MagicMock()
        mock_dal.docker_client = mock_client

        # Mock reading the XML file
        mock_open_ofa.return_value.__enter__.return_value.read.return_value = "<xml>model</xml>"

        # Test agent dictionary
        agent = {
            'ip': None,
            'port': 5000,
            'adapter': {
                'ip': '192.168.0.1',
                'image': None,
                'port': 5001
            },
            'deploy': {
                'resources': {
                    'reservations': {'cpus': 5},
                    'limits': {'cpus': 10}
                },
                'placement': {
                    'constraints': ['node=worker']
                }
            }
        }

        device_uuid = "DEVICE-UUID-123"
        device_xml_uri = "http://example.com/device.xml"

        # Call the method to test
        manager = OpenFactoryManager('http://mocked_url')
        manager.deploy_mtconnect_agent(device_uuid, device_xml_uri, agent)

        # Check that the services.create method was called on the Docker client
        mock_client.services.create.assert_called_once()

        # Extract the call arguments for the create method
        args, kwargs = mock_client.services.create.call_args

        # Check image and network
        self.assertEqual(kwargs['image'], mock_config.MTCONNECT_AGENT_IMAGE)
        self.assertEqual(kwargs['networks'], [mock_config.OPENFACTORY_NETWORK])

        # Expected environment variables (env)
        expected_env = [
            f'MTC_AGENT_UUID={device_uuid.upper()}-AGENT',
            f'ADAPTER_UUID={device_uuid.upper()}',
            f'ADAPTER_IP={agent["adapter"]["ip"]}',
            f'ADAPTER_PORT={agent["adapter"]["port"]}',
            'XML_MODEL=<xml>model</xml>',
            'AGENT_CFG_FILE=mock agent configuration content'
        ]

        # Check that the correct parameters were passed in 'env'
        self.assertIn('env', kwargs)
        self.assertEqual(kwargs['env'], expected_env)

        # Check that the correct resources were passed
        expected_resources = {
            "Limits": {"NanoCPUs": int(1000000000 * agent['deploy']['resources']['limits']['cpus'])},
            "Reservations": {"NanoCPUs": int(1000000000 * agent['deploy']['resources']['reservations']['cpus'])}
        }
        self.assertIn('resources', kwargs)
        self.assertEqual(kwargs['resources'], expected_resources)

        # Check that the correct Docker command was used
        expected_command = "sh -c 'printf \"%b\" \"$XML_MODEL\" > device.xml; printf \"%b\" \"$AGENT_CFG_FILE\" > agent.cfg; mtcagent run agent.cfg'"
        self.assertIn('command', kwargs)
        self.assertEqual(kwargs['command'], expected_command)

        # Check if constraints were handled correctly
        expected_constraints = ['node == worker']
        self.assertIn('constraints', kwargs)
        self.assertEqual(kwargs['constraints'], expected_constraints)

        # Ensure register_asset was called
        mock_register_asset.assert_called_once_with(device_uuid + '-AGENT',
                                                    "MTConnectAgent",
                                                    device_uuid.lower() + '-agent')

        # Ensure the notification method was called
        mock_user_notify.success.assert_called_once_with("Agent device-uuid-123-agent deployed successfully")

    @patch("openfactory.openfactory.KSQL")
    @patch("openfactory.openfactory_manager.dal")
    @patch("openfactory.openfactory_manager.config")
    @patch("openfactory.openfactory_manager.user_notify")
    @patch("openfactory.openfactory_manager.register_asset")
    @patch("openfactory.openfactory_manager.Asset")
    def test_deploy_kafka_producer(self, MockAsset, mock_register_asset, mock_user_notify, mock_config, mock_dal, MockKSQL):
        """
        Test deploy_kafka_producer
        """

        # Mock config values
        mock_config.MTCONNECT_PRODUCER_IMAGE = "mock_producer_image"
        mock_config.KAFKA_BROKER = "mock_kafka_broker"
        mock_config.OPENFACTORY_NETWORK = "mock_network"

        # Set up mocks
        mock_client = MagicMock()
        mock_dal.docker_client = mock_client

        # Test device dictionary
        device = {
            'uuid': 'device-uuid-123',
            'agent': {
                'ip': None,
                'port': 5000,
                'deploy': {
                    'placement': {
                        'constraints': ['node=worker']
                    }
                }
            }
        }

        # Call the method to test
        manager = OpenFactoryManager('http://mocked_url')
        manager.deploy_kafka_producer(device)

        # Check that the services.create method was called on the Docker client
        mock_client.services.create.assert_called_once()

        # Extract the call arguments for the create method
        args, kwargs = mock_client.services.create.call_args

        # Check service_name, image and network
        self.assertEqual(kwargs['name'], device['uuid'].lower() + '-producer')
        self.assertEqual(kwargs['image'], mock_config.MTCONNECT_PRODUCER_IMAGE)
        self.assertEqual(kwargs['networks'], [mock_config.OPENFACTORY_NETWORK])

        # Expected environment variables (env)
        expected_env = [
            f'KAFKA_BROKER={mock_config.KAFKA_BROKER}',
            f'KAFKA_PRODUCER_UUID={device["uuid"]}-PRODUCER',
            f'MTC_AGENT=http://{device["uuid"].lower()}-agent:5000'
        ]

        # Check that the correct parameters were passed in 'env'
        self.assertIn('env', kwargs)
        self.assertEqual(kwargs['env'], expected_env)

        # Check that the correct resources were passed
        expected_resources = {
            "Limits": {"NanoCPUs": int(1000000000 * 0.5)},
            "Reservations": {"NanoCPUs": int(1000000000 * 1.0)}
        }
        self.assertIn('resources', kwargs)
        self.assertEqual(kwargs['resources'], expected_resources)

        # Check if constraints were handled correctly
        expected_constraints = ['node == worker']
        self.assertIn('constraints', kwargs)
        self.assertEqual(kwargs['constraints'], expected_constraints)

        # Ensure register_asset was called
        mock_register_asset.assert_called_once_with(device['uuid'] + '-PRODUCER',
                                                    'KafkaProducer',
                                                    device['uuid'].lower() + '-producer')

        # Ensure the notification method was called
        mock_user_notify.success.assert_called_once_with(f"Kafka producer {device['uuid'].lower()}-producer deployed successfully")

    @patch("openfactory.openfactory.KSQL")
    @patch("openfactory.openfactory_manager.dal")
    @patch("openfactory.openfactory_manager.config")
    @patch("openfactory.openfactory_manager.user_notify")
    @patch("openfactory.openfactory_manager.register_asset")
    @patch("openfactory.openfactory_manager.Asset")
    def test_deploy_device_supervisor(self, mock_Asset, mock_register_asset, mock_user_notify, mock_config, mock_dal, MockKSQL):
        """
        Test deploy_device_supervisor
        """

        # Mock config values
        mock_config.KSQLDB = "mock_ksqldb"
        mock_config.OPENFACTORY_NETWORK = "mock_network"

        # Set up mocks
        mock_client = MagicMock()
        mock_dal.docker_client = mock_client

        # Test supervisor dictionary
        supervisor = {
            'image': 'mock_supervisor_image',
            'adapter': {
                'ip': '192.168.0.1',
                'port': 4444,
                'environment': ['VAR1=value1', 'VAR2=value2']
            },
            'deploy': {
                'resources': {
                    'reservations': {'cpus': 3},
                    'limits': {'cpus': 8}
                },
                'placement': {
                    'constraints': ['node=worker']
                }
            }
        }

        device_uuid = 'DEVICE-UUID-123'

        # Call the method to test
        manager = OpenFactoryManager('http://mocked_url')
        manager.deploy_device_supervisor(device_uuid, supervisor)

        # Check that the services.create method was called on the Docker client
        mock_client.services.create.assert_called_once()

        # Extract the call arguments for the create method
        args, kwargs = mock_client.services.create.call_args

        # Check service_name, image and network
        self.assertEqual(kwargs['name'], device_uuid.lower() + '-supervisor')
        self.assertEqual(kwargs['image'], supervisor['image'])
        self.assertEqual(kwargs['networks'], [mock_config.OPENFACTORY_NETWORK])

        # Expected environment variables (env)
        expected_env = [
            f"DEVICE_UUID={device_uuid}",
            f"KSQL_URL={mock_config.KSQLDB}",
            f"ADAPTER_IP={supervisor['adapter']['ip']}",
            f"ADAPTER_PORT={supervisor['adapter']['port']}",
            'VAR1=value1',
            'VAR2=value2'
        ]

        # Check that the correct parameters were passed in 'env'
        self.assertIn('env', kwargs)
        self.assertEqual(kwargs['env'], expected_env)

        # Check that the correct resources were passed
        expected_resources = {
            "Limits": {"NanoCPUs": int(1000000000 * supervisor['deploy']['resources']['limits']['cpus'])},
            "Reservations": {"NanoCPUs": int(1000000000 * supervisor['deploy']['resources']['reservations']['cpus'])}
        }
        self.assertIn('resources', kwargs)
        self.assertEqual(kwargs['resources'], expected_resources)

        # Check if constraints were handled correctly
        expected_constraints = ['node == worker']
        self.assertIn('constraints', kwargs)
        self.assertEqual(kwargs['constraints'], expected_constraints)

        # Ensure register_asset was called
        mock_register_asset.assert_called_once_with(device_uuid + '-SUPERVISOR', 'Supervisor', device_uuid.lower() + '-supervisor')

        # Ensure the notification method was called
        mock_user_notify.success.assert_called_once_with(f"Supervisor {device_uuid.lower()}-supervisor deployed successfully")

    @patch("openfactory.openfactory.KSQL")
    @patch("openfactory.openfactory_manager.dal")
    @patch("openfactory.openfactory_manager.user_notify")
    @patch("openfactory.openfactory_manager.deregister_asset")
    def test_tear_down_device(self, mock_deregister_asset, mock_user_notify, mock_dal, MockKSQL):
        """
        Test tear_down_device to verify that services are removed and correct notifications are sent
        """

        # Set up mocks for Docker services
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_dal.docker_client = mock_client

        # Mock Docker service get method
        mock_client.services.get.side_effect = lambda name: mock_service if name in [
            'device-uuid-123-adapter',
            'device-uuid-123-producer',
            'device-uuid-123-agent',
            'device-uuid-123-supervisor'
        ] else None

        # Mock the service remove method to simulate successful service removal
        mock_service.remove = MagicMock()

        # Test device_uuid
        device_uuid = 'device-uuid-123'

        # Call the method to test
        manager = OpenFactoryManager('mocked_url')
        manager.tear_down_device(device_uuid)

        # Check that the correct services were removed
        mock_service.remove.assert_called()

        # Check that the correct notifications were sent
        mock_user_notify.success.assert_any_call(f"Adapter for device {device_uuid} shut down successfully")
        mock_user_notify.success.assert_any_call(f"Kafka producer for device {device_uuid} shut down successfully")
        mock_user_notify.success.assert_any_call(f"MTConnect Agent for device {device_uuid} shut down successfully")
        mock_user_notify.success.assert_any_call(f"Supervisor {device_uuid.upper()}-SUPERVISOR removed successfully")
        mock_user_notify.success.assert_any_call(f"{device_uuid} shut down successfully")

        # Ensure deregister_asset was called for all services
        mock_deregister_asset.assert_any_call(device_uuid + '-PRODUCER')
        mock_deregister_asset.assert_any_call(device_uuid + '-AGENT')
        mock_deregister_asset.assert_any_call(f"{device_uuid.upper()}-SUPERVISOR")
        mock_deregister_asset.assert_any_call(device_uuid)

    @patch("openfactory.openfactory.KSQL")
    @patch("openfactory.openfactory_manager.dal")
    @patch("openfactory.openfactory_manager.user_notify")
    def test_tear_down_device_api_error(self, mock_user_notify, mock_dal, MockKSQL):
        """
        Test tear_down_device when an APIError is raised
        """

        # Set up mocks for Docker services
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_dal.docker_client = mock_client

        # Simulate an APIError when trying to remove the service
        mock_service.remove.side_effect = docker.errors.APIError("API error")
        mock_client.services.get.side_effect = lambda name: mock_service

        # Test device_uuid
        device_uuid = 'device-uuid-123'

        # Call the method to test and assert it raises an OFAException
        manager = OpenFactoryManager('mocked_url')
        with self.assertRaises(OFAException):
            manager.tear_down_device(device_uuid)

        # Check if the exception was raised for the service removal
        mock_service.remove.assert_called()
