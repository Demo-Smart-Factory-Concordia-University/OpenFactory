import unittest
import docker
from unittest.mock import patch, MagicMock
from openfactory import OpenFactoryManager
from openfactory.exceptions import OFAException


class TestOpenFactoryManager(unittest.TestCase):
    """
    Tests for class OpenFactoryManager
    """

    @patch("builtins.open", new_callable=MagicMock)
    @patch("openfactory.openfactory_manager.config")
    @patch("openfactory.openfactory_manager.dal")
    @patch("openfactory.openfactory_manager.open_ofa")
    @patch("openfactory.openfactory_manager.user_notify")
    @patch("openfactory.openfactory_manager.register_asset")
    @patch("openfactory.openfactory_manager.Asset")
    def test_deploy_mtconnect_agent(self, MockAsset, mock_register_asset, mock_user_notify, mock_open_ofa, mock_dal, mock_config, mock_open):
        """
        Test deploy_mtconnect_agent
        """

        # Create separate mock instances for device and agent
        mock_device_asset = MagicMock()
        mock_agent_asset = MagicMock()
        MockAsset.side_effect = [mock_device_asset, mock_agent_asset]

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
        ksqlMock = MagicMock()
        manager = OpenFactoryManager(ksqlClient=ksqlMock, bootstrap_servers='mokded_bootstrap_servers')
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
                                                    ksqlClient=ksqlMock,
                                                    bootstrap_servers='mokded_bootstrap_servers',
                                                    docker_service=device_uuid.lower() + '-agent')

        # Check that add_attribute was called with expected parameters
        mock_agent_asset.add_attribute.assert_called_once()
        args, kwargs = mock_agent_asset.add_attribute.call_args

        # Check attribute name
        self.assertEqual(args[0], 'agent_port')

        # Check attribute value (the AssetAttribute instance)
        attr_value = args[1]
        self.assertEqual(attr_value.value, agent['port'])
        self.assertEqual(attr_value.type, 'Events')
        self.assertEqual(attr_value.tag, 'NetworkPort')

        # Ensure the notification method was called
        mock_user_notify.success.assert_called_once_with("Agent device-uuid-123-agent deployed successfully")

    @patch("openfactory.openfactory_manager.dal")
    @patch("openfactory.openfactory_manager.config")
    @patch("openfactory.openfactory_manager.user_notify")
    @patch("openfactory.openfactory_manager.register_asset")
    @patch("openfactory.openfactory_manager.Asset")
    def test_deploy_kafka_producer(self, MockAsset, mock_register_asset, mock_user_notify, mock_config, mock_dal):
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
        ksqlMock = MagicMock()
        manager = OpenFactoryManager(ksqlMock, bootstrap_servers='mokded_bootstrap_servers')
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
            "Limits": {"NanoCPUs": int(1000000000 * 1.0)},
            "Reservations": {"NanoCPUs": int(1000000000 * 0.5)}
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
                                                    ksqlClient=ksqlMock,
                                                    bootstrap_servers='mokded_bootstrap_servers',
                                                    docker_service=device['uuid'].lower() + '-producer')

        # Ensure the notification method was called
        mock_user_notify.success.assert_called_once_with(f"Kafka producer {device['uuid'].lower()}-producer deployed successfully")

    @patch("openfactory.openfactory_manager.dal")
    @patch("openfactory.openfactory_manager.config")
    @patch("openfactory.openfactory_manager.user_notify")
    @patch("openfactory.openfactory_manager.register_asset")
    @patch("openfactory.openfactory_manager.Asset")
    def test_deploy_device_supervisor(self, mock_Asset, mock_register_asset, mock_user_notify, mock_config, mock_dal):
        """
        Test deploy_device_supervisor
        """

        # Mock config values
        mock_config.OPENFACTORY_NETWORK = "mock_network"
        mock_config.KSQLDB_LOG_LEVEL = "MOCK_LOG_LEVEL"

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
        ksqlMock = MagicMock()
        ksqlMock.ksqldb_url = "mock_ksqldb_url"
        manager = OpenFactoryManager(ksqlClient=ksqlMock, bootstrap_servers='mokded_bootstrap_servers')
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
            f"SUPERVISOR_UUID={device_uuid.upper()}-SUPERVISOR",
            f"DEVICE_UUID={device_uuid}",
            "KAFKA_BROKER=mokded_bootstrap_servers",
            "KSQLDB_URL=mock_ksqldb_url",
            f"ADAPTER_IP={supervisor['adapter']['ip']}",
            f"ADAPTER_PORT={supervisor['adapter']['port']}",
            'KSQLDB_LOG_LEVEL=MOCK_LOG_LEVEL',
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
        mock_register_asset.assert_called_once_with(device_uuid + '-SUPERVISOR', 'Supervisor',
                                                    ksqlClient=ksqlMock,
                                                    bootstrap_servers='mokded_bootstrap_servers',
                                                    docker_service=device_uuid.lower() + '-supervisor')

        # Ensure the notification method was called
        mock_user_notify.success.assert_called_once_with(f"Supervisor {device_uuid.lower()}-supervisor deployed successfully")

    @patch("openfactory.openfactory_manager.config")
    @patch('openfactory.openfactory_manager.dal.docker_client')
    @patch('openfactory.openfactory_manager.register_asset')
    @patch('openfactory.openfactory_manager.user_notify')
    def test_deploy_openfactory_application_success(self, mock_user_notify, mock_register_asset, mock_docker_client, mock_config):
        """ Test deploy_openfactory_application """

        # Mock config values
        mock_config.OPENFACTORY_NETWORK = "mock_network"
        mock_config.KSQLDB_LOG_LEVEL = "MOCK_LOG_LEVEL"

        ksqlMock = MagicMock()
        ksqlMock.ksqldb_url = "mock_ksqldb_url"
        manager = OpenFactoryManager(ksqlClient=ksqlMock, bootstrap_servers='mokded_bootstrap_servers')

        application = {
            'uuid': 'test-app',
            'image': 'test-image',
            'environment': ['VAR1=value1', 'VAR2=value2', 'KSQLDB_LOG_LEVEL=MOCK_USER_LOG_LEVEL']
        }

        # Call the method to test
        manager.deploy_openfactory_application(application)

        # Assert
        mock_docker_client.services.create.assert_called_once_with(
            image='test-image',
            name='test-app',
            mode={"Replicated": {"Replicas": 1}},
            env=[
                'APP_UUID=test-app',
                'KAFKA_BROKER=mokded_bootstrap_servers',
                'KSQLDB_URL=mock_ksqldb_url',
                'DOCKER_SERVICE=test-app',
                'VAR1=value1',
                'VAR2=value2',
                'KSQLDB_LOG_LEVEL=MOCK_USER_LOG_LEVEL'
            ],
            networks=['mock_network']
        )
        mock_register_asset.assert_called_once_with(
            'test-app', 'OpenFactoryApp',
            ksqlClient=manager.ksql,
            bootstrap_servers='mokded_bootstrap_servers',
            docker_service='test-app'
        )
        mock_user_notify.success.assert_called_once_with("Application test-app deployed successfully")

    @patch("openfactory.openfactory_manager.config")
    @patch('openfactory.openfactory_manager.dal.docker_client')
    @patch('openfactory.openfactory_manager.user_notify')
    def test_deploy_openfactory_application_failure(self, mock_user_notify, mock_docker_client, mock_config):
        """ Test deploy_openfactory_application when Docker API fails """

        # Mock config values
        mock_config.OPENFACTORY_NETWORK = "mock_network"
        mock_config.KSQLDB_LOG_LEVEL = "MOCK_LOG_LEVEL"

        ksqlMock = MagicMock()
        ksqlMock.ksqldb_url = "mock_ksqldb_url"
        manager = OpenFactoryManager(ksqlClient=ksqlMock, bootstrap_servers='mokded_bootstrap_servers')

        application = {
            'uuid': 'test-app',
            'image': 'test-image',
            'environment': None
        }

        mock_docker_client.services.create.side_effect = docker.errors.APIError("Mocked Docker API error")

        # Call the method to test
        manager.deploy_openfactory_application(application)

        # Assert
        mock_docker_client.services.create.assert_called_once_with(
            image='test-image',
            name='test-app',
            mode={"Replicated": {"Replicas": 1}},
            env=[
                'APP_UUID=test-app',
                'KAFKA_BROKER=mokded_bootstrap_servers',
                'KSQLDB_URL=mock_ksqldb_url',
                'DOCKER_SERVICE=test-app',
                'KSQLDB_LOG_LEVEL=MOCK_LOG_LEVEL'
            ],
            networks=['mock_network']
        )
        mock_user_notify.fail.assert_called_once_with("Application test-app could not be deployed\nMocked Docker API error")

    @patch('openfactory.openfactory_manager.get_apps_from_config_file')
    @patch('openfactory.openfactory_manager.user_notify')
    def test_deploy_apps_from_config_file(self, mock_user_notify, mock_get_apps_from_config_file):
        """ Test deploy_apps_from_config_file """
        # Mock the OpenFactoryManager instance
        ksqlMock = MagicMock()
        ksqlMock.ksqldb_url = "mock_ksqldb_url"
        manager = OpenFactoryManager(ksqlClient=ksqlMock, bootstrap_servers='mokded_bootstrap_servers')
        manager.applications_uuid = MagicMock(return_value=['existing-app-uuid'])
        manager.deploy_openfactory_application = MagicMock()

        # Mock the YAML configuration file loading
        mock_get_apps_from_config_file.return_value = {
            'App1': {'uuid': 'new-app-uuid', 'image': 'app1-image', 'environment': None},
            'App2': {'uuid': 'existing-app-uuid', 'image': 'app2-image', 'environment': None}
        }

        # Call the method to test
        manager.deploy_apps_from_config_file('dummy_config.yaml')

        # Assertions
        mock_get_apps_from_config_file.assert_called_once_with('dummy_config.yaml')
        mock_user_notify.info.assert_any_call('App1:')
        mock_user_notify.info.assert_any_call('App2:')
        mock_user_notify.info.assert_any_call('Application existing-app-uuid exists already and was not deployed')
        manager.deploy_openfactory_application.assert_called_once_with({
            'uuid': 'new-app-uuid',
            'image': 'app1-image',
            'environment': None
        })

    @patch('openfactory.openfactory_manager.get_apps_from_config_file')
    @patch('openfactory.openfactory_manager.user_notify')
    def test_deploy_apps_from_config_file_no_apps(self, mock_user_notify, mock_get_apps_from_config_file):
        """ Test deploy_apps_from_config_file when no apps are found in the config file """
        # Mock the OpenFactoryManager instance
        ksqlMock = MagicMock()
        ksqlMock.ksqldb_url = "mock_ksqldb_url"
        manager = OpenFactoryManager(ksqlClient=ksqlMock, bootstrap_servers='mokded_bootstrap_servers')

        # Mock the YAML configuration file loading to return None
        mock_get_apps_from_config_file.return_value = None

        # Call the method to test
        manager.deploy_apps_from_config_file('dummy_config.yaml')

        # Assertions
        mock_get_apps_from_config_file.assert_called_once_with('dummy_config.yaml')
        mock_user_notify.info.assert_not_called()

    @patch("openfactory.openfactory_manager.dal")
    @patch("openfactory.openfactory_manager.user_notify")
    @patch("openfactory.openfactory_manager.deregister_asset")
    def test_tear_down_device(self, mock_deregister_asset, mock_user_notify, mock_dal):
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
        ksqlMock = MagicMock()
        manager = OpenFactoryManager(ksqlMock, bootstrap_servers='mokded_bootstrap_servers')
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
        mock_deregister_asset.assert_any_call(device_uuid + '-PRODUCER', ksqlClient=ksqlMock, bootstrap_servers='mokded_bootstrap_servers')
        mock_deregister_asset.assert_any_call(device_uuid + '-AGENT', ksqlClient=ksqlMock, bootstrap_servers='mokded_bootstrap_servers')
        mock_deregister_asset.assert_any_call(f"{device_uuid.upper()}-SUPERVISOR", ksqlClient=ksqlMock, bootstrap_servers='mokded_bootstrap_servers')
        mock_deregister_asset.assert_any_call(device_uuid, ksqlClient=ksqlMock, bootstrap_servers='mokded_bootstrap_servers')

    @patch("openfactory.openfactory_manager.dal")
    @patch("openfactory.openfactory_manager.user_notify")
    def test_tear_down_device_api_error(self, mock_user_notify, mock_dal):
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
        ksqlMock = MagicMock()
        manager = OpenFactoryManager(ksqlMock, bootstrap_servers='mocked_bootstrap_servers')
        with self.assertRaises(OFAException):
            manager.tear_down_device(device_uuid)

        # Check if the exception was raised for the service removal
        mock_service.remove.assert_called()

    @patch("openfactory.openfactory_manager.Asset")
    @patch("openfactory.openfactory_manager.dal")
    @patch("openfactory.openfactory_manager.user_notify")
    @patch("openfactory.openfactory_manager.deregister_asset")
    def test_tear_down_application(self, mock_deregister_asset, mock_user_notify, mock_dal, MockAsset):
        """
        Test tear_down_application to verify that applications are removed and correct notifications are sent
        """

        # Mock Asset instance and its DockerService value
        mock_app_instance = MagicMock()
        mock_app_instance.DockerService.value = "mock-service-name"
        MockAsset.return_value = mock_app_instance

        # Set up mocks for Docker services
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_dal.docker_client = mock_client

        # Mock Docker service get method
        mock_client.services.get.side_effect = lambda name: mock_service if name == 'mock-service-name' else None

        # Mock the service remove method to simulate successful service removal
        mock_service.remove = MagicMock()

        # Test device_uuid
        app_uuid = 'app-uuid-123'

        # Call the method to test
        ksqlMock = MagicMock()
        manager = OpenFactoryManager(ksqlMock, bootstrap_servers='mocked_bootstrap_servers')
        manager.tear_down_application(app_uuid)

        # Check that the correct services were removed
        mock_service.remove.assert_called()

        # Check that the correct notifications were sent
        mock_user_notify.success.assert_any_call(f"OpenFactory application {app_uuid} shut down successfully")

        # Ensure deregister_asset was called
        mock_deregister_asset.assert_any_call(app_uuid, ksqlClient=ksqlMock, bootstrap_servers='mocked_bootstrap_servers')

    @patch("openfactory.openfactory_manager.Asset")
    @patch("openfactory.openfactory_manager.dal")
    @patch("openfactory.openfactory_manager.user_notify")
    @patch("openfactory.openfactory_manager.deregister_asset")
    def test_tear_down_application_no_docker_service(self, mock_deregister_asset, mock_user_notify, mock_dal, MockAsset):
        """
        Test tear_down_application when application is not deployed as a Docker service
        """

        # Mock Asset instance and its DockerService value
        mock_app_instance = MagicMock()
        mock_app_instance.DockerService.value = "mock-service-name"
        MockAsset.return_value = mock_app_instance

        # Set up mocks for Docker services
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_dal.docker_client = mock_client

        # Mock Docker service get method
        def mock_get_service(name):
            if name == "mock-service-name":
                raise docker.errors.NotFound("Service not found")
            return mock_service  # Return the mock service for other names
        mock_client.services.get.side_effect = mock_get_service

        # Mock the service remove method to simulate successful service removal
        mock_service.remove = MagicMock()

        # Test device_uuid
        app_uuid = 'app-uuid-123'

        # Call the method to test
        ksqlMock = MagicMock()
        manager = OpenFactoryManager(ksqlMock, bootstrap_servers='mocked_bootstrap_servers')
        manager.tear_down_application(app_uuid)

        # Ensure deregister_asset was called
        mock_deregister_asset.assert_any_call(app_uuid, ksqlClient=ksqlMock, bootstrap_servers='mocked_bootstrap_servers')

        # No success message
        mock_user_notify.assert_not_called()

    @patch("openfactory.openfactory_manager.Asset")
    @patch("openfactory.openfactory_manager.dal")
    @patch("openfactory.openfactory_manager.user_notify")
    @patch("openfactory.openfactory_manager.deregister_asset")
    def test_tear_down_application_docker_api_error(self, mock_deregister_asset, mock_user_notify, mock_dal, MockAsset):
        """
        Test tear_down_application handels Docker API errors
        """

        # Mock Asset instance and its DockerService value
        mock_app_instance = MagicMock()
        mock_app_instance.DockerService.value = "mock-service-name"
        MockAsset.return_value = mock_app_instance

        # Set up mocks for Docker services
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_dal.docker_client = mock_client

        # Mock Docker service get method
        def mock_get_service(name):
            if name == "mock-service-name":
                raise docker.errors.APIError("Docker error")
            return mock_service  # Return the mock service for other names
        mock_client.services.get.side_effect = mock_get_service

        # Mock the service remove method to simulate successful service removal
        mock_service.remove = MagicMock()

        # Test device_uuid
        app_uuid = 'app-uuid-123'

        # Call the method to test
        ksqlMock = MagicMock()
        manager = OpenFactoryManager(ksqlMock, bootstrap_servers='mocked_bootstrap_servers')
        with self.assertRaises(OFAException):
            manager.tear_down_application(app_uuid)

        # Ensure deregister_asset was not called
        mock_deregister_asset.assert_not_called()

        # No success message
        mock_user_notify.assert_not_called()

    @patch('openfactory.openfactory_manager.get_apps_from_config_file')
    @patch('openfactory.openfactory_manager.user_notify')
    def test_shut_down_apps_from_config_file(self, mock_user_notify, mock_get_apps_from_config_file):
        """ Test shut_down_apps_from_config_file """
        # Mock the OpenFactoryManager instance
        ksqlMock = MagicMock()
        ksqlMock.ksqldb_url = "mock_ksqldb_url"
        manager = OpenFactoryManager(ksqlClient=ksqlMock, bootstrap_servers='mokded_bootstrap_servers')
        manager.applications_uuid = MagicMock(return_value=['app-uuid-1', 'app-uuid-2'])
        manager.tear_down_application = MagicMock()

        # Mock the YAML config file content
        mock_get_apps_from_config_file.return_value = {
            'App1': {'uuid': 'app-uuid-1'},
            'App2': {'uuid': 'app-uuid-3'}
        }

        # Call the method
        manager.shut_down_apps_from_config_file('dummy_config.yaml')

        # Assertions
        mock_get_apps_from_config_file.assert_called_once_with('dummy_config.yaml')
        mock_user_notify.info.assert_any_call('App1:')
        mock_user_notify.info.assert_any_call('App2:')
        mock_user_notify.info.assert_any_call('No application app-uuid-3 deployed in OpenFactory')
        manager.tear_down_application.assert_called_once_with('app-uuid-1')

    @patch('openfactory.openfactory_manager.get_apps_from_config_file')
    def test_shut_down_apps_from_config_file_no_apps(self, mock_get_apps_from_config_file):
        """ Test shut_down_apps_from_config_file when no apps are found in the config file """
        # Mock the OpenFactoryManager instance
        ksqlMock = MagicMock()
        ksqlMock.ksqldb_url = "mock_ksqldb_url"
        manager = OpenFactoryManager(ksqlClient=ksqlMock, bootstrap_servers='mokded_bootstrap_servers')

        # Mock the YAML config file returning None
        mock_get_apps_from_config_file.return_value = None

        # Call the method
        manager.shut_down_apps_from_config_file('dummy_config.yaml')

        # Assertions
        mock_get_apps_from_config_file.assert_called_once_with('dummy_config.yaml')
