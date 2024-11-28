import os
import time
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
INFLUXDB_PUSH_INTERVAL = int(os.getenv('INFLUXDB_PUSH_INTERVAL', 10))

# Connect to InfluxDB
influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

# ksqlDB configuration
ksqldb_server = 'ksqldb-server'
ksqldb_port = 8088


def process_ksql_row(samples_df):
    """
    Convert a ksqlDB row to InfluxDB format and write to the database.
    """
    try:
        for _, row in samples_df.iterrows():
            try:
                val = float(row["VALUE"])
                point = (
                    Point(DEVICE_UUID)
                    .tag("tag", row["TAG"])
                    .field(row["ID"], val)
                    .time(row["TIMESTAMP"], write_precision="ms")
                )
                # Write the point to InfluxDB
                if DEBUG:
                    print(point)
                write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
            except ValueError:
                if DEBUG:
                    print(f"Device is unavailable or does not send proper data. Got {row['ID']}={row['VALUE']}")
                continue

    except Exception as e:
        print(f"Failed to process ksqlDB row: {e}")


"""
Continuously fetch and process rows from the ksqlDB device table.
"""
device_table = DEVICE_UUID.replace('-', '_')
print("======================================================")
print("InfluxDB connector for   ", DEVICE_UUID)
print("Reading from ksqlDB table", device_table)
print("InfluxDB url:         ", INFLUXDB_URL)
print("InfluxDB organisation:", INFLUXDB_ORG)
print("InfluxDB bucket:      ", INFLUXDB_BUCKET)
print("Push interval:        ", INFLUXDB_PUSH_INTERVAL)
print("======================================================")

ksql = KSQL(f'http://{ksqldb_server}:{ksqldb_port}')
query = f"SELECT ROWTIME AS timestamp, ID, VALUE, TAG FROM {device_table} WHERE TYPE='Samples';"
while True:
    df = asyncio.run(ksql.query_to_dataframe(query))
    process_ksql_row(df)
    time.sleep(INFLUXDB_PUSH_INTERVAL)
