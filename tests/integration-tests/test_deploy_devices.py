import os
from unittest import TestCase
from click.testing import CliRunner
from openfactory import OpenFactory
from openfactory.ofacli import cli
from openfactory.assets import Asset
from openfactory.ofa.ksqldb import ksql
from openfactory.docker.docker_access_layer import dal
import openfactory.config as config


class TestDeployDevices(TestCase):
    """
    Integration tests for device deployment
    """

    def test_deploy_and_shutdown_single_device(self):
        """ Test deployment of a single device """
        runner = CliRunner()
        config_file = os.path.join(os.path.dirname(__file__), "configs", "temp.yml")

        # Deploy
        result_up = runner.invoke(cli, ["device", "up", config_file])
        print("\n---- ofa device up ----")
        print(result_up.output)
        print("-----------------------")
        self.assertEqual(result_up.exit_code, 0, msg=result_up.output)

        # Check if device is deployed
        ofa = OpenFactory(ksqlClient=ksql.client)
        self.assertIn('TEMP-001', ofa.devices_uuid(), 'Device [TEMP-001] is not deployed as expected')
        self.assertIn('TEMP-001-AGENT', ofa.agents_uuid(), 'Agent of [TEMP-001] is not deployed as expected')
        self.assertIn('TEMP-001-PRODUCER', ofa.producers_uuid(), 'Producer of [TEMP-001] is not deployed as expected')
        self.assertNotIn('TEMP-001-SUPERVISOR', ofa.supervisors_uuid(), 'An unexpected supervisor was deployed')

        # Check availability of assets
        sensor = Asset('TEMP-001', ksqlClient=ksql.client, bootstrap_servers=config.KAFKA_BROKER)
        self.assertTrue(sensor.wait_until('avail', 'AVAILABLE', timeout=15), 'Sensor [TEMP-001] did not become available before timeout')
        self.assertEqual(sensor.avail.value, 'AVAILABLE', 'Sensor [TEMP-001] is not available as it should')
        expected_attributes = [
            'AssetType', 'DockerService', 'Temp', 'avail',
            'dht_asset_chg', 'dht_asset_count', 'dht_asset_rem',
            'references_above', 'references_below'
        ]
        actual = sensor.attributes()
        self.assertCountEqual(actual, expected_attributes, 'The attributes of [TEMP-001] are not as expected')
        self.assertEqual(sensor.references_above_uuid(), [], 'The references above of [TEMP-001] are not as expected')
        self.assertCountEqual(sensor.references_below_uuid(), ['TEMP-001-PRODUCER', 'TEMP-001-AGENT'], 'The references below of [TEMP-001] are not as expected')

        agent = Asset('TEMP-001-AGENT', ksqlClient=ksql.client, bootstrap_servers=config.KAFKA_BROKER)
        self.assertEqual(agent.agent_avail.value, 'AVAILABLE', 'Agent of [TEMP-001] is not available as it should')
        producer = Asset('TEMP-001-PRODUCER', ksqlClient=ksql.client, bootstrap_servers=config.KAFKA_BROKER)
        self.assertEqual(producer.avail.value, 'AVAILABLE', 'Producer of [TEMP-001] is not available as it should')

        # Tear down
        result_down = runner.invoke(cli, ["device", "down", config_file])
        self.assertEqual(result_down.exit_code, 0, msg=result_down.output)
        print("\n---- ofa device down ----")
        print(result_down.output)
        print("-------------------------")
        self.assertEqual(result_up.exit_code, 0, msg=result_up.output)
        self.assertNotIn('TEMP-001', ofa.devices_uuid(), 'Device [TEMP-001] is not removed as expected')
        self.assertNotIn('TEMP-001-AGENT', ofa.agents_uuid(), 'Agent of [TEMP-001] is not removed as expected')
        self.assertNotIn('TEMP-001-PRODUCER', ofa.producers_uuid(), 'Producer of [TEMP-001] is not removed as expected')

    def test_deploy_and_shutdown_adapter(self):
        """ Test deployment of an adapter """
        runner = CliRunner()
        config_file = os.path.join(os.path.dirname(__file__), "configs", "temp_adapt.yml")

        # Deploy
        result_up = runner.invoke(cli, ["device", "up", config_file])
        print("\n---- ofa device up ----")
        print(result_up.output)
        print("-----------------------")
        self.assertEqual(result_up.exit_code, 0, msg=result_up.output)

        # Check if device is deployed
        ofa = OpenFactory(ksqlClient=ksql.client)
        self.assertIn('TEMP-002', ofa.devices_uuid(), 'Device [TEMP-002] is not deployed as expected')
        self.assertIn('TEMP-002-AGENT', ofa.agents_uuid(), 'Agent of [TEMP-002] is not deployed as expected')
        self.assertIn('TEMP-002-PRODUCER', ofa.producers_uuid(), 'Producer of [TEMP-002] is not deployed as expected')
        self.assertNotIn('TEMP-002-SUPERVISOR', ofa.supervisors_uuid(), 'An unexpected supervisor was deployed')

        # Check availability of assets
        sensor = Asset('TEMP-002', ksqlClient=ksql.client, bootstrap_servers=config.KAFKA_BROKER)
        self.assertTrue(sensor.wait_until('avail', 'AVAILABLE', timeout=15), 'Sensor [TEMP-002] did not become available before timeout')
        self.assertEqual(sensor.avail.value, 'AVAILABLE', 'Sensor [TEMP-002] is not available as it should')
        expected_attributes = [
            'AssetType', 'DockerService', 'Temp', 'avail',
            'dht_asset_chg', 'dht_asset_count', 'dht_asset_rem',
            'references_above', 'references_below'
        ]
        actual = sensor.attributes()
        self.assertCountEqual(actual, expected_attributes, 'The attributes of [TEMP-002] are not as expected')
        self.assertEqual(sensor.references_above_uuid(), [], 'The references above of [TEMP-002] are not as expected')
        self.assertCountEqual(sensor.references_below_uuid(), ['TEMP-002-PRODUCER', 'TEMP-002-AGENT'], 'The references below of [TEMP-002] are not as expected')

        agent = Asset('TEMP-002-AGENT', ksqlClient=ksql.client, bootstrap_servers=config.KAFKA_BROKER)
        self.assertEqual(agent.agent_avail.value, 'AVAILABLE', 'Agent of [TEMP-002] is not available as it should')
        producer = Asset('TEMP-002-PRODUCER', ksqlClient=ksql.client, bootstrap_servers=config.KAFKA_BROKER)
        self.assertEqual(producer.avail.value, 'AVAILABLE', 'Producer of [TEMP-002] is not available as it should')

        # Tear down
        result_down = runner.invoke(cli, ["device", "down", config_file])
        self.assertEqual(result_down.exit_code, 0, msg=result_down.output)
        print("\n---- ofa device down ----")
        print(result_down.output)
        print("-------------------------")
        self.assertEqual(result_up.exit_code, 0, msg=result_up.output)
        self.assertNotIn('TEMP-002', ofa.devices_uuid(), 'Device [TEMP-002] is not removed as expected')
        self.assertNotIn('TEMP-002-AGENT', ofa.agents_uuid(), 'Agent of [TEMP-002] is not removed as expected')
        self.assertNotIn('TEMP-002-PRODUCER', ofa.producers_uuid(), 'Producer of [TEMP-002] is not removed as expected')

    def test_deploy_and_shutdown_ofa_app(self):
        """ Test deployment of an OpenFactory application """
        runner = CliRunner()
        config_file = os.path.join(os.path.dirname(__file__), "configs", "app.yml")

        # Deploy
        result_up = runner.invoke(cli, ["apps", "up", config_file])
        print("\n---- ofa device up ----")
        print(result_up.output)
        print("-----------------------")
        self.assertEqual(result_up.exit_code, 0, msg=result_up.output)

        # Check if app is deployed
        ofa = OpenFactory(ksqlClient=ksql.client)

        # Check availability of app
        app = Asset('TEST-APP', ksqlClient=ksql.client, bootstrap_servers=config.KAFKA_BROKER)
        res = app.wait_until('avail', 'AVAILABLE', timeout=15, use_ksqlDB=True)
        self.assertIn('TEST-APP', ofa.applications_uuid(), 'App [TEST-APP] is not deployed as expected')
        self.assertTrue(res, 'App [TEST-APP] did not become available before timeout')
        self.assertEqual(app.avail.value, 'AVAILABLE', 'App [TEST-APP] is not AVAILABLE as it should')

        # Check Docker service of the app is deployed
        services = dal.docker_client.services.list()
        service_names = [service.name for service in services]
        self.assertIn(
            app.DockerService.value,
            service_names,
            f"Service '{app.DockerService.value}' is not running."
        )

        # Tear down
        result_down = runner.invoke(cli, ["apps", "down", config_file])
        self.assertEqual(result_down.exit_code, 0, msg=result_down.output)
        print("\n---- ofa device down ----")
        print(result_down.output)
        print("-------------------------")

        # Check availability of app
        self.assertEqual(app.avail.value, 'UNAVAILABLE', 'App [TEST-APP] is not UNAVAILABLE as it should')

        # Check Docker service of the app was removed
        services = dal.docker_client.services.list()
        service_names = [service.name for service in services]
        self.assertNotIn(
            app.DockerService.value,
            service_names,
            f"Service '{app.DockerService.value}' is still running."
        )
