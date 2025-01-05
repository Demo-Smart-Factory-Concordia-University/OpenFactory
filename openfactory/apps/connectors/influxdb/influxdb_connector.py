from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from ..sinkconnector import SinkConnector


class InfluxDBConnector(SinkConnector):
    """
    InfluxDB connector
    """

    DEBUG = False

    def connectInfluxDB(self, url, token, org, bucket, measuremnt_name):
        """ Connect to InfluxDB """
        self.INFLUXDB_URL = url
        self.INFLUXDB_TOKEN = token
        self.INFLUXDB_ORG = org
        self.INFLUXDB_BUCKET = bucket
        self.measuremnt_name = measuremnt_name

        # Connect to InfluxDB
        self.influx_client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)

    def stream_query(self):
        query = f"""
                 SELECT ROWTIME AS timestamp,
                    ID,
                    REGEXP_REPLACE(tag, '\\{{[^}}]*\\}}', '') AS TAG, -- remove XML namesape
                    VALUE
                 FROM {self.service_stream}
                 WHERE TYPE = 'Samples'
                 EMIT CHANGES;
                """
        return query

    async def new_data(self, data):
        """
        Convert a ksqlDB row to InfluxDB format and send it to the database.
        """
        try:
            try:
                val = float(data[3])
                point = (
                    Point(self.measuremnt_name)
                    .tag("tag", data[2])
                    .field(data[1], val)
                    .time(data[0], write_precision="ms")
                )
                # Write the point to InfluxDB
                if self.DEBUG:
                    print(point)
                self.write_api.write(bucket=self.INFLUXDB_BUCKET, org=self.INFLUXDB_ORG, record=point)
            except ValueError:
                if self.DEBUG:
                    print(f"Device is unavailable or does not send proper data. Got {data['ID']}={data['VALUE']}")

        except Exception as e:
            print(f"Failed to process ksqlDB message: {e}")
