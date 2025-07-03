"""
Interface to the OpenFactory API.

Defines the `OpenFactory` class, which provides methods to interact
with deployed assets, devices, and services via KSQL queries to OpenFactory.
"""

from pandas import DataFrame
from typing import List
import openfactory.config as config
from openfactory.assets import Asset
from openfactory.kafka.ksql import KSQLDBClient


class OpenFactory:
    """
    Main API to OpenFactory.

    Provides access to deployed assets, their availability, Docker services,
    and their classification by type (devices, agents, etc.).
    """

    def __init__(self, ksqlClient: KSQLDBClient, bootstrap_servers: str = config.KAFKA_BROKER):
        """
        Initialize the OpenFactory API.

        Args:
            ksqlClient (KSQLDBClient): A client capable of executing KSQL queries.
            bootstrap_servers (str): Kafka bootstrap server address.
        """
        self.bootstrap_servers = bootstrap_servers
        self.ksql = ksqlClient

    def assets_uuid(self) -> List[str]:
        """
        Get list of asset UUIDs deployed on OpenFactory.

        Returns:
            List[str]: UUIDs of all deployed assets.
        """
        query = "SELECT ASSET_UUID FROM assets_type;"
        df = self.ksql.query(query)
        return df['ASSET_UUID'].to_list() if not df.empty else []

    def assets(self) -> List[Asset]:
        """
        Get list of Asset objects deployed on OpenFactory.

        Returns:
            List[Asset]: Deployed Asset instances.
        """
        return [Asset(uuid, self.ksql, self.bootstrap_servers) for uuid in self.assets_uuid()]

    def assets_availability(self) -> DataFrame:
        """
        Get availability data for all deployed assets.

        Returns:
            DataFrame: Availability data of deployed assets.
        """
        query = "SELECT * FROM assets_avail;"
        return self.ksql.query(query)

    def assets_docker_services(self) -> DataFrame:
        """
        Get Docker services associated with all deployed assets.

        Returns:
            DataFrame: Docker services data of deployed assets.
        """
        query = "SELECT * FROM docker_services;"
        return self.ksql.query(query)

    def devices_uuid(self) -> List[str]:
        """
        Get UUIDs of all devices deployed on OpenFactory.

        Returns:
            List[str]: UUIDs of deployed device-type assets.
        """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'Device';"
        df = self.ksql.query(query)
        return df['ASSET_UUID'].to_list() if not df.empty else []

    def devices(self) -> List[Asset]:
        """
        Get Asset objects corresponding to deployed devices.

        Returns:
            List[Asset]: Deployed device-type assets.
        """
        return [Asset(uuid, self.ksql, self.bootstrap_servers) for uuid in self.devices_uuid()]

    def agents_uuid(self) -> List[str]:
        """
        Get UUIDs of deployed MTConnect agents.

        Returns:
            List[str]: UUIDs of deployed MTConnect agents.
        """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'MTConnectAgent';"
        df = self.ksql.query(query)
        return df['ASSET_UUID'].to_list() if not df.empty else []

    def agents(self) -> List[Asset]:
        """
        Get `Asset` objects corresponding to deployed MTConnect agents.

        Returns:
            List[Asset]: Deployed MTConnect agent assets.
        """
        return [Asset(uuid, self.ksql, self.bootstrap_servers) for uuid in self.agents_uuid()]

    def producers_uuid(self) -> List[str]:
        """
        Get UUIDs of deployed Kafka producers.

        Returns:
            List[str]: UUIDs of deployed Kafka producer assets.
        """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'KafkaProducer';"
        df = self.ksql.query(query)
        return df['ASSET_UUID'].to_list() if not df.empty else []

    def producers(self) -> List[Asset]:
        """
        Get Asset objects corresponding to deployed Kafka producers.

        Returns:
            List[Asset]: Kafka producer assets.
        """
        return [Asset(uuid, self.ksql, self.bootstrap_servers) for uuid in self.producers_uuid()]

    def supervisors_uuid(self) -> List[str]:
        """
        Get UUIDs of deployed Supervisors.

        Returns:
            List[str]: UUIDs of deployed supervisor-type assets.
        """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'Supervisor';"
        df = self.ksql.query(query)
        return df['ASSET_UUID'].to_list() if not df.empty else []

    def supervisors(self) -> List[Asset]:
        """
        Get Asset objects corresponding to deployed Supervisors.

        Returns:
            List[Asset]: Deployed supervisor-type assets.
        """
        return [Asset(uuid, self.ksql, self.bootstrap_servers) for uuid in self.supervisors_uuid()]

    def applications_uuid(self) -> List[str]:
        """
        Get UUIDs of deployed OpenFactory applications.

        Returns:
            List[str]: UUIDs of deployed OpenFactory application-type assets.
        """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'OpenFactoryApp';"
        df = self.ksql.query(query)
        return df['ASSET_UUID'].to_list() if not df.empty else []

    def applications(self) -> List[Asset]:
        """
        Get Asset objects corresponding to deployed OpenFactory applications.

        Returns:
            List[Asset]: Deployed OpenFactory application-type assets.
        """
        return [Asset(uuid, self.ksql, self.bootstrap_servers) for uuid in self.applications_uuid()]
