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
            List[str]: UUIDs of all assets.
        """
        query = "SELECT ASSET_UUID FROM assets_type;"
        df = self.ksql.query(query)
        return df['ASSET_UUID'].to_list() if not df.empty else []

    def assets(self) -> List[Asset]:
        """
        Get list of Asset objects deployed on OpenFactory.

        Returns:
            List[Asset]: Asset instances.
        """
        return [Asset(uuid, self.ksql, self.bootstrap_servers) for uuid in self.assets_uuid()]

    def assets_availability(self) -> DataFrame:
        """
        Get availability data for all assets.

        Returns:
            pandas.DataFrame: Availability data.
        """
        query = "SELECT * FROM assets_avail;"
        return self.ksql.query(query)

    def assets_docker_services(self) -> DataFrame:
        """
        Get Docker services associated with all assets.

        Returns:
            pandas.DataFrame: Docker services data.
        """
        query = "SELECT * FROM docker_services;"
        return self.ksql.query(query)

    def devices_uuid(self) -> List[str]:
        """
        Get UUIDs of all devices deployed on OpenFactory.

        Returns:
            List[str]: UUIDs of device-type assets.
        """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'Device';"
        df = self.ksql.query(query)
        return df['ASSET_UUID'].to_list() if not df.empty else []

    def devices(self) -> List[Asset]:
        """
        Get Asset objects corresponding to devices.

        Returns:
            List[Asset]: Device assets.
        """
        return [Asset(uuid, self.ksql, self.bootstrap_servers) for uuid in self.devices_uuid()]

    def agents_uuid(self) -> List[str]:
        """
        Get UUIDs of MTConnect agents.

        Returns:
            List[str]: UUIDs of MTConnect agents.
        """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'MTConnectAgent';"
        df = self.ksql.query(query)
        return df['ASSET_UUID'].to_list() if not df.empty else []

    def agents(self) -> List[Asset]:
        """
        Get Asset objects corresponding to MTConnect agents.

        Returns:
            List[Asset]: MTConnect agent assets.
        """
        return [Asset(uuid, self.ksql, self.bootstrap_servers) for uuid in self.agents_uuid()]

    def producers_uuid(self) -> List[str]:
        """
        Get UUIDs of Kafka producers.

        Returns:
            List[str]: UUIDs of Kafka producer assets.
        """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'KafkaProducer';"
        df = self.ksql.query(query)
        return df['ASSET_UUID'].to_list() if not df.empty else []

    def producers(self) -> List[Asset]:
        """
        Get Asset objects corresponding to Kafka producers.

        Returns:
            List[Asset]: Kafka producer assets.
        """
        return [Asset(uuid, self.ksql, self.bootstrap_servers) for uuid in self.producers_uuid()]

    def supervisors_uuid(self) -> List[str]:
        """
        Get UUIDs of Supervisors.

        Returns:
            List[str]: UUIDs of Supervisor assets.
        """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'Supervisor';"
        df = self.ksql.query(query)
        return df['ASSET_UUID'].to_list() if not df.empty else []

    def supervisors(self) -> List[Asset]:
        """
        Get Asset objects corresponding to Supervisors.

        Returns:
            List[Asset]: Supervisor assets.
        """
        return [Asset(uuid, self.ksql, self.bootstrap_servers) for uuid in self.supervisors_uuid()]

    def applications_uuid(self) -> List[str]:
        """
        Get UUIDs of OpenFactory applications.

        Returns:
            List[str]: UUIDs of OpenFactory application assets.
        """
        query = "SELECT ASSET_UUID FROM assets_type WHERE TYPE = 'OpenFactoryApp';"
        df = self.ksql.query(query)
        return df['ASSET_UUID'].to_list() if not df.empty else []

    def applications(self) -> List[Asset]:
        """
        Get Asset objects corresponding to OpenFactory applications.

        Returns:
            List[Asset]: OpenFactory application assets.
        """
        return [Asset(uuid, self.ksql, self.bootstrap_servers) for uuid in self.applications_uuid()]
