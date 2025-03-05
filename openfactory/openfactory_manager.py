import asyncio
import docker
import openfactory.config as config
from openfactory import OpenFactory
from openfactory.assets import Asset
from openfactory.docker.docker_access_layer import dal
from openfactory.exceptions import OFAException
from openfactory.models.user_notifications import user_notify
from openfactory.utils import get_nested, open_ofa, register_asset, deregister_asset


class OpenFactoryManager(OpenFactory):
    """
    OpenFactory Manager API

    Allows to deploy services on OpenFactory
    User requires Docker access on the OpenFactory cluster
    """

    def deploy_mtconnect_agent(self, device_uuid, device_xml_uri, agent):
        """
        Deploy an MTConnect agent
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
        try:
            dal.docker_client.services.create(
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
                endpoint_spec=docker.types.EndpointSpec(ports={agent_port: 5000}),
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
        register_asset(agent_uuid, "MTConnectAgent", service_name)
        device = Asset(device_uuid, self.ksqldb_url)
        device.add_reference_below(agent_uuid)
        agent = Asset(agent_uuid, self.ksqldb_url)
        agent.add_reference_above(device_uuid)

        user_notify.success(f"Agent {device_uuid.lower()}-agent deployed successfully")

    def deploy_mtconnect_adapter(self, device_uuid, adapter):
        """
        Deploy an MTConnect adapter
        """
        client = dal.docker_client

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
            client.services.create(
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

    def deploy_kafka_producer(self, device):
        """
        Deploy a Kafka producer
        """

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
        producer_uuid = device['uuid'] + '-PRODUCER'
        try:
            dal.docker_client.services.create(
                image=config.MTCONNECT_PRODUCER_IMAGE,
                name=service_name,
                mode={"Replicated": {"Replicas": 1}},
                env=[f'KAFKA_BROKER={config.KAFKA_BROKER}',
                     f'KAFKA_PRODUCER_UUID={producer_uuid}',
                     f'MTC_AGENT={MTC_AGENT}'],
                constraints=constraints,
                resources={
                    "Limits": {"NanoCPUs": int(1000000000*0.5)},
                    "Reservations": {"NanoCPUs": int(1000000000*1.0)}
                    },
                networks=[config.OPENFACTORY_NETWORK]
            )
        except docker.errors.APIError as err:
            raise OFAException(f"Producer {service_name} could not be created\n{err}")

        # register producer in OpenFactory
        register_asset(producer_uuid, "KafkaProducer", service_name)
        dev = Asset(device['uuid'], self.ksqldb_url)
        dev.add_reference_below(producer_uuid)
        producer = Asset(producer_uuid, self.ksqldb_url)
        producer.add_reference_above(device['uuid'])

        user_notify.success(f"Kafka producer {service_name} deployed successfully")

    def deploy_device_supervisor(self, device_uuid, supervisor):
        """
        Deploy an OpenFactory device supervisor
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
        env = [f"DEVICE_UUID={device_uuid}",
               f"KSQL_URL={config.KSQLDB}",
               f"ADAPTER_IP={supervisor['adapter']['ip']}",
               f"ADAPTER_PORT={supervisor['adapter']['port']}"]

        if supervisor['adapter']['environment'] is not None:
            for item in supervisor['adapter']['environment']:
                var, val = item.split('=')
                env.append(f"{var.strip()}={val.strip()}")

        try:
            dal.docker_client.services.create(
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
        supervisor_uuid = f"{device_uuid.upper()}-SUPERVISOR"
        register_asset(supervisor_uuid, 'Supervisor', device_uuid.lower() + '-supervisor')
        device = Asset(device_uuid, self.ksqldb_url)
        device.add_reference_below(supervisor_uuid)
        supervisor = Asset(supervisor_uuid, self.ksqldb_url)
        supervisor.add_reference_above(device_uuid)

        user_notify.success(f"Supervisor {device_uuid.lower()}-supervisor deployed successfully")

    def create_device_ksqldb_tables(self, device_uuid, ksql_tables):
        """
        Create ksqlDB tables of an OpenFactory device
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

    def tear_down_device(self, device_uuid):
        """
        Tear down a device deployed on OpenFactory
        """

        # tear down Adapter
        try:
            service = dal.docker_client.services.get(device_uuid.lower() + '-adapter')
            service.remove()
            user_notify.success(f"Adapter for device {device_uuid} shut down successfully")
        except docker.errors.NotFound:
            # no adapter running as a Docker swarm service
            pass
        except docker.errors.APIError as err:
            raise OFAException(err)

        # tear down Producer
        try:
            service = dal.docker_client.services.get(device_uuid.lower() + '-producer')
            service.remove()
            deregister_asset(device_uuid+'-PRODUCER')
            user_notify.success(f"Kafka producer for device {device_uuid} shut down successfully")
        except docker.errors.NotFound:
            user_notify.info(f"Kafka producer for device {device_uuid} was not running")
        except docker.errors.APIError as err:
            raise OFAException(err)

        # tear down Agent
        try:
            service = dal.docker_client.services.get(device_uuid.lower() + '-agent')
            service.remove()
            # self.send_unavailable()
            deregister_asset(device_uuid + '-AGENT')
            user_notify.success(f"MTConnect Agent for device {device_uuid} shut down successfully")
        except docker.errors.NotFound:
            # no agent running as a Docker swarm service
            pass
        except docker.errors.APIError as err:
            raise OFAException(err)

        # tear down Supervisor
        try:
            supervisor_service = dal.docker_client.services.get(device_uuid.lower() + '-supervisor')
            supervisor_service.remove()
            deregister_asset(f"{device_uuid.upper()}-SUPERVISOR")
            user_notify.success(f"Supervisor {device_uuid.upper()}-SUPERVISOR removed successfully")
        except docker.errors.NotFound:
            # no supervisor
            pass
        except docker.errors.APIError as err:
            raise OFAException(err)

        deregister_asset(device_uuid)
        user_notify.success(f"{device_uuid} shut down successfully")

    def get_asset_uuid_from_docker_service(self, docker_service_name):
        """
        Return ASSET_UUID of the asset running on the Docker service docker_service_name
        """
        query = f"select ASSET_UUID from DOCKER_SERVICES where DOCKER_SERVICE='{docker_service_name}';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        if df.empty:
            return ""
        return df['ASSET_UUID'][0]
