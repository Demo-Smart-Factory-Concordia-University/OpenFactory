from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from openfactory.exceptions import OFAConfigurationException


class DataAccessLayer:

    engine = None
    conn_uri = None

    def connect(self):
        if self.conn_uri is None:
            raise OFAConfigurationException('DataAccessLayer.conn_uri has to be defined')
        self.engine = create_engine(self.conn_uri)
        self.session = Session(self.engine)


db = DataAccessLayer()
