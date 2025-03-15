import asyncio
from httpx import RequestError
from pyksql.ksql import KSQL
import openfactory.config as config
from openfactory.exceptions import OFAException
from openfactory.assets import Asset


class OpenFactory:
    """
    Main API to OpenFactory
    """

    def __init__(self, ksqldb_url=config.KSQLDB, bootstrap_servers=config.KAFKA_BROKER):
        self.bootstrap_servers = bootstrap_servers
        self.ksqldb_url = ksqldb_url
        self.ksql = KSQL(ksqldb_url)
        try:
            self.ksql.info()
        except RequestError as err:
            raise OFAException(f'Could not connect to {ksqldb_url}: {err}')

    def assets(self):
        """ Return list of assets deployed on OpenFactory """
        query = "SELECT * FROM assets_type;"
        df = asyncio.run(self.ksql.query_to_dataframe(query))

        if df.empty:
            return []

        return [Asset(asset_uuid=row.ASSET_UUID, ksqldb_url=self.ksqldb_url) for row in df.itertuples()]

    def assets_availability(self):
        """ Return availability of OpenFactory assets """
        query = "SELECT * FROM assets_avail;"
        return asyncio.run(self.ksql.query_to_dataframe(query))

    def assets_docker_services(self):
        """ Return Docker services of OpenFactory assets """
        query = "SELECT * FROM docker_services;"
        return asyncio.run(self.ksql.query_to_dataframe(query))

    def devices_uuid(self):
        """ Return list of asset_uuid of devices deployed on OpenFactory """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'Device';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return df['ASSET_UUID'].to_list()

    def devices(self):
        """ Return devices deployed on OpenFactory """
        return [Asset(uuid, self.ksqldb_url, self.bootstrap_servers) for uuid in self.devices_uuid()]

    def agents_uuid(self):
        """ Return list of asset_uuid of MTConnect agents deployed on OpenFactory """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'MTConnectAgent';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return df['ASSET_UUID'].to_list()

    def agents(self):
        """ Return MTConnect agents deployed on OpenFactory """
        return [Asset(uuid, self.ksqldb_url, self.bootstrap_servers) for uuid in self.agents_uuid()]

    def producers_uuid(self):
        """ Return list of asset_uuid of Kafka producers deployed on OpenFactory """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'KafkaProducer';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return df['ASSET_UUID'].to_list()

    def producers(self):
        """ Return Kafka producers deployed on OpenFactory """
        return [Asset(uuid, self.ksqldb_url, self.bootstrap_servers) for uuid in self.producers_uuid()]

    def supervisors_uuid(self):
        """ Return list of asset_uuid of Supervisors deployed on OpenFactory """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'Supervisor';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return df['ASSET_UUID'].to_list()

    def supervisors(self):
        """ Return Supervisors deployed on OpenFactory """
        return [Asset(uuid, self.ksqldb_url, self.bootstrap_servers) for uuid in self.supervisors_uuid()]

    def applications_uuid(self):
        """ Return list of asset_uuid of Applications deployed on OpenFactory """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'OpenFactoryApp';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return df['ASSET_UUID'].to_list()

    def applications(self):
        """ Return Applications deployed on OpenFactory """
        return [Asset(uuid, self.ksqldb_url, self.bootstrap_servers) for uuid in self.applications_uuid()]
