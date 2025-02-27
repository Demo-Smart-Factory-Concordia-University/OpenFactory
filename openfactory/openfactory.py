import asyncio
from httpx import RequestError
from pyksql.ksql import KSQL
import openfactory.config as config
from openfactory.exceptions import OFAException
from openfactory.assets.asset import Asset


class OpenFactory:
    """
    Main API to OpenFactory
    """

    def __init__(self, ksqldb_url=config.KSQLDB):
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

        return [Asset(asset_uuid=row.ASSET_UUID) for row in df.itertuples()]

    def assets_availability(self):
        """ Return availability of OpenFactory assets """
        query = "SELECT * FROM assets_avail;"
        return asyncio.run(self.ksql.query_to_dataframe(query))

    def assets_docker_services(self):
        """ Return Docker services of OpenFactory assets """
        query = "SELECT * FROM docker_services;"
        return asyncio.run(self.ksql.query_to_dataframe(query))

    def devices(self):
        """ Return devices deployed on OpenFactory """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'Device';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        if df.empty:
            return []
        return [Asset(asset_uuid=row.ASSET_UUID) for row in df.itertuples()]

    def agents(self):
        """ Return MTConnect agents deployed on OpenFactory """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'MTConnectAgent';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return df['ASSET_UUID'].to_list()

    def producers(self):
        """ Return Kafka producers deployed on OpenFactory """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'KafkaProducer';"
        df = asyncio.run(self.ksql.query_to_dataframe(query))
        return df['ASSET_UUID'].to_list()
