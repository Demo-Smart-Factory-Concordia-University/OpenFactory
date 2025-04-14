from openfactory.kafka import KSQLDBClient


class KSQLDBAccessLayer:

    client = None

    def connect(self, ksqldb_url):
        self.client = KSQLDBClient(ksqldb_url=ksqldb_url)
        self.client.info()


ksql = KSQLDBAccessLayer()
