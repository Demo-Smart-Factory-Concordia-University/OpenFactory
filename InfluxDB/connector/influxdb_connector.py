import os
import asyncio
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from pyksql.ksql import KSQL

DEBUG = os.getenv('DEBUG', 0)

# Device to connect to InfluxDB
DEVICE_UUID = os.getenv('DEVICE_UUID')

# InfluxDB configuration
INFLUXDB_URL = os.getenv('INFLUXDB_URL')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET')

# Connect to InfluxDB
influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

# ksqlDB configuration
ksqldb_server = 'ksqldb-server'
ksqldb_port = 8088


def process_ksql_row(row):
    """
    Convert a ksqlDB row to InfluxDB format and write to the database.
    """
    try:
        try:
            val = float(row[3])
            point = (
                Point(DEVICE_UUID)
                .tag("tag", row[2])
                .field(row[1], val)
                .time(row[0], write_precision="ms")
            )
            # Write the point to InfluxDB
            if DEBUG:
                print(point)
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
        except ValueError:
            if DEBUG:
                print(f"Device is unavailable or does not send proper data. Got {row['ID']}={row['VALUE']}")

    except Exception as e:
        print(f"Failed to process ksqlDB message: {e}")


async def fetch_streaming_data(device_stream):
    """
    Continuously fetch and process rows from the ksqlDB device stream
    """
    ksql = KSQL(f'http://{ksqldb_server}:{ksqldb_port}')
    query = f"""
        SELECT ROWTIME AS timestamp,
            ID,
            REGEXP_REPLACE(tag, '\\{{[^}}]*\\}}', '')) AS TAG,
            VALUE
        FROM {device_stream}
        WHERE TYPE = 'Samples'
        EMIT CHANGES;
        """

    try:
        await ksql.query(
            query=query,
            earliest=False,
            on_new_row=process_ksql_row
        )
    except Exception as e:
        print(f"An error occurred: {e}")


"""
Main code
"""
device_stream = DEVICE_UUID.replace('-', '_') + '_STREAM'
print("======================================================")
print("InfluxDB connector for    ", DEVICE_UUID)
print("Reading from ksqlDB stream", device_stream)
print("InfluxDB url:         ", INFLUXDB_URL)
print("InfluxDB organisation:", INFLUXDB_ORG)
print("InfluxDB bucket:      ", INFLUXDB_BUCKET)
print("======================================================")

asyncio.run(fetch_streaming_data(device_stream))
