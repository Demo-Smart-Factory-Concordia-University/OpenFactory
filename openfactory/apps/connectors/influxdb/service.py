import os
from .influxdb_connector import InfluxDBConnector

DEBUG = os.getenv('DEBUG', 0)

# Device to connect to InfluxDB
DEVICE_UUID = os.getenv('DEVICE_UUID')

# ksqlDB server
KSQLDB_URL = os.getenv('KSQLDB_URL', "http://ksqldb-server:8088")

# InfluxDB configuration
INFLUXDB_URL = os.getenv('INFLUXDB_URL')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET')

if __name__ == "__main__":
    """
    OpenFactory InfluxDB connetor
    """
    device_stream = DEVICE_UUID.replace('-', '_') + '_STREAM'

    connector = InfluxDBConnector(
        connector_uuid=DEVICE_UUID.replace('-', '_') + '_INFLUXDB_CONNECTOR',
        service_stream=device_stream,
        ksql_url=KSQLDB_URL
    )

    print("======================================================")
    print("InfluxDB connector for    ", DEVICE_UUID)
    print("Reading from ksqlDB stream", device_stream)
    print("InfluxDB url:         ", INFLUXDB_URL)
    print("InfluxDB organisation:", INFLUXDB_ORG)
    print("InfluxDB bucket:      ", INFLUXDB_BUCKET)
    print("======================================================")

    connector.connectInfluxDB(url=INFLUXDB_URL,
                              token=INFLUXDB_TOKEN,
                              org=INFLUXDB_ORG,
                              bucket=INFLUXDB_BUCKET,
                              measuremnt_name=DEVICE_UUID)
    connector.run()
