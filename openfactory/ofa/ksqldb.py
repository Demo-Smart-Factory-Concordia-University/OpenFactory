""" OpenFactory access layer for KSQLDB client. """

from openfactory.kafka import KSQLDBClient


class KSQLDBAccessLayer:
    """ Access layer for KSQLDB client. """

    client = None

    def connect(self, ksqldb_url: str) -> None:
        """
        Connect to KSQLDB server.

        Args:
            ksqldb_url (str): URL of the KSQLDB server.
        """
        self.client = KSQLDBClient(ksqldb_url=ksqldb_url)
        self.client.info()


ksql = KSQLDBAccessLayer()
