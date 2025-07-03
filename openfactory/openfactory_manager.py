"""
OpenFactory Manager API.

Provides functionality for managing the OpenFactory system.

It includes the `OpenFactoryManager` class, which facilitates the deployment of MTConnect agents
and other related operations such as registering assets, handling configurations, and managing Docker services.

The module interacts with Docker for container management, as well as with OpenFactory services to integrate deployed agents
into the system, along with error handling, user notifications, and resource management.
"""

import docker
import os
from fsspec.core import split_protocol
from typing import Dict, Optional

import openfactory.config as config
from openfactory import OpenFactory
from openfactory.schemas.devices import get_devices_from_config_file
from openfactory.schemas.apps import get_apps_from_config_file
from openfactory.assets import Asset, AssetAttribute
from openfactory.exceptions import OFAException
from openfactory.models.user_notifications import user_notify
from openfactory.utils import get_nested, open_ofa, register_asset, deregister_asset
from openfactory.kafka.ksql import KSQLDBClient
from openfactory.openfactory_deploy_strategy import OpenFactoryServiceDeploymentStrategy, SwarmDeploymentStrategy


class OpenFactoryManager(OpenFactory):
    """
    OpenFactory Manager API.

    Allows to deploy services on OpenFactory.

    Important:
        User requires Docker access on the OpenFactory cluster.

    Attributes:
        deployment_strategy (OpenFactoryServiceDeploymentStrategy): The strategy used to deploy services.
    """

    def __init__(self, ksqlClient: KSQLDBClient,
                 bootstrap_servers: str = config.KAFKA_BROKER,
                 deployment_strategy: Optional[OpenFactoryServiceDeploymentStrategy] = None):
        """
        Initializes the OpenFactoryManager.

        Args:
            ksqlClient (KSQLDBClient): The client for interacting with ksqlDB.
            bootstrap_servers (str): The Kafka bootstrap server address. Defaults to config.KAFKA_BROKER.
            deployment_strategy (Optional[OpenFactoryServiceDeploymentStrategy]):
                The deployment strategy to use (e.g., Swarm or Local). If not provided, defaults to SwarmDeploymentStrategy.
        """
        super().__init__(ksqlClient, bootstrap_servers)
        self.deployment_strategy = deployment_strategy or SwarmDeploymentStrategy()

    def deploy_mtconnect_agent(self, device_uuid: str, device_xml_uri: str, agent: Dict) -> None:
        """
        Deploy an MTConnect agent.

        Args:
            device_uuid (str): The UUID of the device.
            device_xml_uri (str): URI to the device's XML model.
            agent (dict): The agent configuration as a dictionary.

        Raises:
            OFAException: If the agent cannot be deployed.
        """
        # if external agent nothing to deploy
        if agent['ip']:
            return

        # compute ressources
        cpus_reservation = get_nested(agent, ['deploy', 'resources', 'reservations', 'cpus'], 0.5)
        cpus_limit = get_nested(agent, ['deploy', 'resources', 'limits', 'cpus'], 1)

        # compute placement constraints
        placement_constraints = get_nested(agent, ['deploy', 'placement', 'constraints'])
        if placement_constraints:
            constraints = [
                constraint.replace('=', ' == ') for constraint in placement_constraints
                ]
        else:
            constraints = None

        # compute adapter IP
        if agent['adapter']['image']:
            adapter_ip = device_uuid.lower() + '-adapter'
            self.deploy_mtconnect_adapter(device_uuid=device_uuid,
                                          adapter=agent['adapter'])
        else:
            adapter_ip = agent['adapter']['ip']

        # load device xml model from source based on xml model uri
        xml_model = ""
        try:
            with open_ofa(device_xml_uri) as f_remote:
                xml_model += f_remote.read()
        except (OFAException, FileNotFoundError) as err:
            user_notify.fail(f"Could not load XML device model {device_xml_uri}.\n{err}")

        # deploy agent on Docker swarm cluster
        try:
            with open(config.MTCONNECT_AGENT_CFG_FILE, 'r') as file:
                agent_cfg = file.read()
        except FileNotFoundError:
            raise OFAException(f"Could not find the MTConnect model file '{config.MTCONNECT_AGENT_CFG_FILE}'")

        command = "sh -c 'printf \"%b\" \"$XML_MODEL\" > device.xml; printf \"%b\" \"$AGENT_CFG_FILE\" > agent.cfg; mtcagent run agent.cfg'"
        service_name = device_uuid.lower() + '-agent'
        agent_uuid = device_uuid.upper() + '-AGENT'
        agent_port = agent['port']

        # configuration for Traefik
        labels = {
                "traefik.enable": "true",
                f"traefik.http.routers.{service_name}.rule": f"Host(`{device_uuid.lower()}.agent.{config.OPENFACTORY_DOMAIN}`)",
                f"traefik.http.routers.{service_name}.entrypoints": "web",
                f"traefik.http.services.{service_name}.loadbalancer.server.port": "5000"
            }

        try:
            self.deployment_strategy.deploy(
                image=config.MTCONNECT_AGENT_IMAGE,
                command=command,
                name=service_name,
                mode={"Replicated": {"Replicas": 1}},
                env=[f'MTC_AGENT_UUID={agent_uuid}',
                     f'ADAPTER_UUID={device_uuid.upper()}',
                     f'ADAPTER_IP={adapter_ip}',
                     f'ADAPTER_PORT={agent["adapter"]["port"]}',
                     f'XML_MODEL={xml_model}',
                     f'AGENT_CFG_FILE={agent_cfg}'],
                ports={agent_port: 5000},
                labels=labels,
                networks=[config.OPENFACTORY_NETWORK],
                resources={
                    "Limits": {"NanoCPUs": int(1000000000*cpus_limit)},
                    "Reservations": {"NanoCPUs": int(1000000000*cpus_reservation)}
                    },
                constraints=constraints
            )
        except docker.errors.APIError as err:
            raise OFAException(err)

        # register agent in OpenFactory
        register_asset(agent_uuid, "MTConnectAgent",
                       ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers, docker_service=service_name)
        device = Asset(device_uuid, ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers)
        device.add_reference_below(agent_uuid)
        agent = Asset(agent_uuid, ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers)
        agent.add_reference_above(device_uuid)
        agent.add_attribute('agent_port',
                            AssetAttribute(
                                value=agent_port,
                                type='Events',
                                tag='NetworkPort'
                            ))

        user_notify.success(f"Agent {agent_uuid} deployed successfully")

    def deploy_mtconnect_adapter(self, device_uuid: str, adapter: Dict) -> None:
        """
        Deploy an MTConnect adapter.

        Args:
            device_uuid (str): The UUID of the device.
            adapter (dict): The adapter configuration as a dictionary.

        Raises:
            OFAException: If the adapter cannot be deployed.
        """
        # compute ressources
        cpus_reservation = get_nested(adapter, ['deploy', 'resources', 'reservations', 'cpus'], 0.5)
        cpus_limit = get_nested(adapter, ['deploy', 'resources', 'limits', 'cpus'], 1)

        # compute placement constraints
        placement_constraints = get_nested(adapter, ['deploy', 'placement', 'constraints'])
        if placement_constraints:
            constraints = [
                constraint.replace('=', ' == ') for constraint in placement_constraints
                ]
        else:
            constraints = None

        # compute environment variables
        env = []
        if adapter['environment'] is not None:
            for item in adapter['environment']:
                var, val = item.split('=')
                env.append(f"{var.strip()}={val.strip()}")

        # deploy adapter on Docker swarm cluster
        try:
            self.deployment_strategy.deploy(
                image=adapter['image'],
                name=device_uuid.lower() + '-adapter',
                mode={"Replicated": {"Replicas": 1}},
                env=env,
                constraints=constraints,
                networks=[config.OPENFACTORY_NETWORK],
                resources={
                    "Limits": {"NanoCPUs": int(1000000000*cpus_limit)},
                    "Reservations": {"NanoCPUs": int(1000000000*cpus_reservation)}
                    }
            )
        except docker.errors.APIError as err:
            user_notify.fail(f"Adapter {device_uuid.lower()}-adapter could not be deployed\n{err}")
            return
        user_notify.success(f"Adapter {device_uuid.lower()}-adapter deployed successfully")

    def deploy_kafka_producer(self, device: Dict) -> None:
        """
        Deploy a Kafka producer.

        Args:
            device (dict): The device configuration as a dictionary.

        Raises:
            OFAException: If the producer cannot be deployed.
        """
        # compute ressources
        cpus_reservation = get_nested(device, ['agent', 'deploy', 'resources', 'reservations', 'cpus'], 0.5)
        cpus_limit = get_nested(device, ['agent', 'deploy', 'resources', 'limits', 'cpus'], 1)

        # compute placement constraints
        placement_constraints = get_nested(device, ['agent', 'deploy', 'placement', 'constraints'])
        if placement_constraints:
            constraints = [
                constraint.replace('=', ' == ') for constraint in placement_constraints
                ]
        else:
            constraints = None

        if device['agent']['ip']:
            if device['agent']['port'] == 443:
                MTC_AGENT = f"https://{device['agent']['ip']}:443"
            else:
                MTC_AGENT = f"http://{device['agent']['ip']}:{device['agent']['port']}"
        else:
            MTC_AGENT = f"http://{device['uuid'].lower()}-agent:5000"

        service_name = device['uuid'].lower() + '-producer'
        producer_uuid = device['uuid'].upper() + '-PRODUCER'
        try:
            self.deployment_strategy.deploy(
                image=config.MTCONNECT_PRODUCER_IMAGE,
                name=service_name,
                mode={"Replicated": {"Replicas": 1}},
                env=[f'KAFKA_BROKER={config.KAFKA_BROKER}',
                     f'KAFKA_PRODUCER_UUID={producer_uuid}',
                     f'MTC_AGENT={MTC_AGENT}'],
                constraints=constraints,
                resources={
                    "Limits": {"NanoCPUs": int(1000000000*cpus_limit)},
                    "Reservations": {"NanoCPUs": int(1000000000*cpus_reservation)}
                    },
                networks=[config.OPENFACTORY_NETWORK]
            )
        except docker.errors.APIError as err:
            raise OFAException(f"Producer {service_name} could not be created\n{err}")

        # register producer in OpenFactory
        register_asset(producer_uuid, "KafkaProducer",
                       ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers, docker_service=service_name)
        dev = Asset(device['uuid'], ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers)
        dev.add_reference_below(producer_uuid)
        producer = Asset(producer_uuid, ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers)
        producer.add_reference_above(device['uuid'])

        user_notify.success(f"Kafka producer {producer_uuid} deployed successfully")

    def deploy_device_supervisor(self, device_uuid: str, supervisor: Dict) -> None:
        """
        Deploy an OpenFactory device supervisor.

        Args:
            device_uuid (str): The UUID of the device.
            supervisor (dict): The supervisor configuration as a dictionary.

        Raises:
            OFAException: If the supervisor cannot be deployed.
        """
        # compute ressources
        cpus_reservation = get_nested(supervisor, ['deploy', 'resources', 'reservations', 'cpus'], 0.5)
        cpus_limit = get_nested(supervisor, ['deploy', 'resources', 'limits', 'cpus'], 1)

        # compute placement constraints
        placement_constraints = get_nested(supervisor, ['deploy', 'placement', 'constraints'])
        if placement_constraints:
            constraints = [
                constraint.replace('=', ' == ') for constraint in placement_constraints
                ]
        else:
            constraints = None

        # build environment variables
        supervisor_uuid = f"{device_uuid.upper()}-SUPERVISOR"
        env = [f"SUPERVISOR_UUID={supervisor_uuid}",
               f"DEVICE_UUID={device_uuid}",
               f"KAFKA_BROKER={self.bootstrap_servers}",
               f"KSQLDB_URL={self.ksql.ksqldb_url}",
               f"ADAPTER_IP={supervisor['adapter']['ip']}",
               f"ADAPTER_PORT={supervisor['adapter']['port']}",
               f"KSQLDB_LOG_LEVEL={config.KSQLDB_LOG_LEVEL}"]

        if supervisor['adapter']['environment'] is not None:
            for item in supervisor['adapter']['environment']:
                var, val = item.split('=')
                env.append(f"{var.strip()}={val.strip()}")

        try:
            self.deployment_strategy.deploy(
                image=supervisor['image'],
                name=device_uuid.lower() + '-supervisor',
                mode={"Replicated": {"Replicas": 1}},
                env=env,
                networks=[config.OPENFACTORY_NETWORK],
                resources={
                    "Limits": {"NanoCPUs": int(1000000000*cpus_limit)},
                    "Reservations": {"NanoCPUs": int(1000000000*cpus_reservation)}
                    },
                constraints=constraints
            )
        except docker.errors.APIError as err:
            user_notify.fail(f"Supervisor {device_uuid.lower()}-supervisor could not be deployed\n{err}")
            return
        register_asset(supervisor_uuid, 'Supervisor',
                       ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers, docker_service=device_uuid.lower() + '-supervisor')
        device = Asset(device_uuid, ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers)
        device.add_reference_below(supervisor_uuid)
        supervisor = Asset(supervisor_uuid, ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers)
        supervisor.add_reference_above(device_uuid)

        user_notify.success(f"Supervisor {supervisor_uuid} deployed successfully")

    def deploy_openfactory_application(self, application: Dict) -> None:
        """
        Deploy an OpenFactory application.

        Args:
            application (dict): The application configuration as a dictionary.

        Raises:
            OFAException: If the application cannot be deployed.
        """
        # build environment variables
        env = [f"APP_UUID={application['uuid']}",
               f"KAFKA_BROKER={self.bootstrap_servers}",
               f"KSQLDB_URL={self.ksql.ksqldb_url}",
               f"DOCKER_SERVICE={application['uuid'].lower()}"]
        if application['environment'] is not None:
            for item in application['environment']:
                var, val = item.split('=')
                env.append(f"{var.strip()}={val.strip()}")

        # if KSQLDB_LOG_LEVEL is not set by user, set it to the default value
        if not any(var.startswith("KSQLDB_LOG_LEVEL=") for var in env):
            env.append(f"KSQLDB_LOG_LEVEL={config.KSQLDB_LOG_LEVEL}")

        try:
            self.deployment_strategy.deploy(
                image=application['image'],
                name=application['uuid'].lower(),
                mode={"Replicated": {"Replicas": 1}},
                env=env,
                networks=[config.OPENFACTORY_NETWORK]
            )
        except docker.errors.APIError as err:
            user_notify.fail(f"Application {application['uuid']} could not be deployed\n{err}")
            return

        register_asset(application['uuid'], 'OpenFactoryApp',
                       ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers, docker_service=application['uuid'].lower())
        user_notify.success(f"Application {application['uuid']} deployed successfully")

    def deploy_devices_from_config_file(self, yaml_config_file: str) -> None:
        """
        Deploy OpenFactory devices based on a yaml configuration file.

        Args:
            yaml_config_file (str): Path to the yaml configuration file.

        Raises:
            OFAException: If the device cannot be deployed.
        """
        # load yaml description file
        devices = get_devices_from_config_file(yaml_config_file)
        if devices is None:
            return

        for dev_name, device in devices.items():
            user_notify.info(f"{dev_name}:")
            if device['uuid'] in self.devices_uuid():
                user_notify.info(f"Device {device['uuid']} exists already and was not deployed")
                continue

            # compute device device xml uri
            if device['agent']['ip']:
                device_xml_uri = ""
            else:
                device_xml_uri = device['agent']['device_xml']
                protocol, _ = split_protocol(device_xml_uri)
                if not protocol:
                    if not os.path.isabs(device_xml_uri):
                        device_xml_uri = os.path.join(os.path.dirname(yaml_config_file), device_xml_uri)

            register_asset(device['uuid'], "Device", ksqlClient=self.ksql, docker_service="")

            self.deploy_mtconnect_agent(device_uuid=device['uuid'],
                                        device_xml_uri=device_xml_uri,
                                        agent=device['agent'])

            self.deploy_kafka_producer(device)

            if device['ksql_tables']:
                self.create_device_ksqldb_tables(device_uuid=device['uuid'],
                                                 ksql_tables=device['ksql_tables'])

            if device['supervisor']:
                self.deploy_device_supervisor(device_uuid=device['uuid'],
                                              supervisor=device['supervisor'])

            user_notify.success(f"Device {device['uuid']} deployed successfully")

    def deploy_apps_from_config_file(self, yaml_config_file: str) -> None:
        """
        Deploy OpenFactory applications based on a yaml configuration file.

        Args:
            yaml_config_file (str): Path to the yaml configuration file.

        Raises:
            OFAException: If the application cannot be deployed.
        """
        # load yaml description file
        apps = get_apps_from_config_file(yaml_config_file)
        if apps is None:
            return

        for app_name, app in apps.items():
            user_notify.info(f"{app_name}:")
            if app['uuid'] in self.applications_uuid():
                user_notify.info(f"Application {app['uuid']} exists already and was not deployed")
                continue

            self.deploy_openfactory_application(app)

    def create_device_ksqldb_tables(self, device_uuid: str, ksql_tables: list) -> None:
        """
        Create ksqlDB tables of an OpenFactory device.

        Args:
            device_uuid (str): The UUID of the device.
            ksql_tables (list): List of ksqlDB tables to create.

        Raises:
            OFAException: If the ksqlDB tables cannot be created.
        """
        if ksql_tables is None:
            return

        if 'device' in ksql_tables:
            # device stream
            self.ksql._statement_query(f"""CREATE STREAM {device_uuid.replace('-', '_')}_STREAM AS
                                            SELECT *
                                            FROM devices_stream
                                            WHERE device_uuid = '{device_uuid}';""")
            user_notify.success((f"ksqlDB stream {device_uuid.replace('-', '_')}_STREAM created successfully"))
            # device table
            self.ksql._statement_query(f"""CREATE TABLE IF NOT EXISTS {device_uuid.replace('-', '_')} AS
                                             SELECT id,
                                                    LATEST_BY_OFFSET(value) AS value,
                                                    LATEST_BY_OFFSET(type) AS type,
                                                    LATEST_BY_OFFSET(REGEXP_REPLACE(tag, '\\{{[^}}]*\\}}', '')) AS tag
                                             FROM devices_stream
                                             WHERE device_uuid = '{device_uuid}'
                                             GROUP BY id;""")
            user_notify.success((f"ksqlDB table {device_uuid.replace('-', '_')} created successfully"))
        if 'agent' in ksql_tables:
            # agent table
            self.ksql._statement_query(f"""CREATE TABLE IF NOT EXISTS {device_uuid.replace('-', '_')}_AGENT AS
                                             SELECT id,
                                                    LATEST_BY_OFFSET(value) AS value,
                                                    LATEST_BY_OFFSET(type) AS type,
                                                    LATEST_BY_OFFSET(REGEXP_REPLACE(tag, '\\{{[^}}]*\\}}', '')) AS tag
                                             FROM devices_stream
                                             WHERE device_uuid = '{device_uuid}-AGENT'
                                             GROUP BY id;""")
            user_notify.success((f"ksqlDB table {device_uuid.replace('-', '_')}_AGENT created successfully"))
        if 'producer' in ksql_tables:
            # producer table
            self.ksql._statement_query(f"""CREATE TABLE IF NOT EXISTS {device_uuid.replace('-', '_')}_PRODUCER AS
                                             SELECT id,
                                                    LATEST_BY_OFFSET(value) AS value,
                                                    LATEST_BY_OFFSET(type) AS type,
                                                    LATEST_BY_OFFSET(REGEXP_REPLACE(tag, '\\{{[^}}]*\\}}', '')) AS tag
                                             FROM devices_stream
                                             WHERE device_uuid = '{device_uuid}-PRODUCER'
                                             GROUP BY id;""")
            user_notify.success((f"ksqlDB table {device_uuid.replace('-', '_')}_PRODUCER created successfully"))

    def tear_down_device(self, device_uuid: str) -> None:
        """
        Tear down a device deployed on OpenFactory.

        Args:
            device_uuid (str): The UUID of the device to be torn down.

        Raises:
            OFAException: If the device cannot be torn down.
        """
        # tear down Adapter
        try:
            self.deployment_strategy.remove(device_uuid.lower() + '-adapter')
            user_notify.success(f"Adapter for device {device_uuid} shut down successfully")
        except docker.errors.NotFound:
            # no adapter running as a Docker swarm service
            pass
        except docker.errors.APIError as err:
            raise OFAException(err)

        # tear down Producer
        try:
            self.deployment_strategy.remove(device_uuid.lower() + '-producer')
            deregister_asset(device_uuid + '-PRODUCER', ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers)
            user_notify.success(f"Kafka producer for device {device_uuid} shut down successfully")
        except docker.errors.NotFound:
            user_notify.info(f"Kafka producer for device {device_uuid} was not running")
        except docker.errors.APIError as err:
            raise OFAException(err)

        # tear down Agent
        try:
            self.deployment_strategy.remove(device_uuid.lower() + '-agent')
            deregister_asset(device_uuid + '-AGENT', ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers)
            user_notify.success(f"MTConnect Agent for device {device_uuid} shut down successfully")
        except docker.errors.NotFound:
            # no agent running as a Docker swarm service
            pass
        except docker.errors.APIError as err:
            raise OFAException(err)

        # tear down Supervisor
        try:
            self.deployment_strategy.remove(device_uuid.lower() + '-supervisor')
            deregister_asset(f"{device_uuid.upper()}-SUPERVISOR", ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers)
            user_notify.success(f"Supervisor for device {device_uuid} shut down successfully")
        except docker.errors.NotFound:
            # no supervisor
            pass
        except docker.errors.APIError as err:
            raise OFAException(err)

        deregister_asset(device_uuid, ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers)
        user_notify.success(f"Device {device_uuid} shut down successfully")

    def shut_down_devices_from_config_file(self, yaml_config_file: str) -> None:
        """
        Shut down devices based on a config file.

        Args:
            yaml_config_file (str): Path to the yaml configuration file.

        Raises:
            OFAException: If the device cannot be shut down.
        """
        # Load yaml description file
        devices = get_devices_from_config_file(yaml_config_file)
        if devices is None:
            return

        uuid_list = [device.asset_uuid for device in self.devices()]

        for dev_name, device in devices.items():
            user_notify.info(f"{dev_name}:")
            if not device['uuid'] in uuid_list:
                user_notify.info(f"No device {device['uuid']} deployed in OpenFactory")
                continue

            self.tear_down_device(device['uuid'])

    def tear_down_application(self, app_uuid: str) -> None:
        """
        Tear down a deployed OpenFactory application.

        Args:
            app_uuid (str): The UUID of the application to be torn down.

        Raises:
            OFAException: If the application cannot be torn down.
        """
        try:
            app = Asset(app_uuid, ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers)
            self.deployment_strategy.remove(app.DockerService.value)
        except docker.errors.NotFound:
            # the application was not running as a Docker swarm service
            deregister_asset(app_uuid, ksqlClient=self.ksql)
            pass
        except docker.errors.APIError as err:
            raise OFAException(err)
        deregister_asset(app_uuid, ksqlClient=self.ksql, bootstrap_servers=self.bootstrap_servers)
        user_notify.success(f"OpenFactory application {app_uuid} shut down successfully")

    def shut_down_apps_from_config_file(self, yaml_config_file: str) -> None:
        """
        Shut down OpenFactory applications based on a config file.

        Args:
            yaml_config_file (str): Path to the yaml configuration file.

        Raises:
            OFAException: If the application cannot be shut down.
        """
        # Load yaml description file
        apps = get_apps_from_config_file(yaml_config_file)
        if apps is None:
            return

        for app_name, app in apps.items():
            user_notify.info(f"{app_name}:")
            if not app['uuid'] in self.applications_uuid():
                user_notify.info(f"No application {app['uuid']} deployed in OpenFactory")
                continue

            self.tear_down_application(app['uuid'])

    def get_asset_uuid_from_docker_service(self, docker_service_name: str) -> str:
        """
        Return ASSET_UUID of the asset running on the Docker service docker_service_name.

        Args:
            docker_service_name (str): The name of the Docker service.

        Returns:
            str: The ASSET_UUID of the asset running on the Docker service.
        """
        query = f"select ASSET_UUID from DOCKER_SERVICES where DOCKER_SERVICE='{docker_service_name}';"
        df = self.ksql.query(query)
        if df.empty:
            return ""
        return df['ASSET_UUID'][0]
