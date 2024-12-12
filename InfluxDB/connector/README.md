# OpenFactory InfluxDB connector
This folder contains the code for the OpenFactory InfluxDB connector.

## Docker image
The GitHub workflow [influxdb_connector.yml](../../.github/workflows/influxdb_connector.yml) creates the Docker image and pushes it to DockerHub. This image is used by OpenFacotry to deploy InfluxDB connectors for devices. 

The variable `INFLUXDB_CONNECTOR_IMAGE` in the OpenFactory configuration file [openfactory.yml](../../openfactory/config/openfactory.yml) points to this image. If the image create from the GitHub workflow is used this would be:
```
INFLUXDB_CONNECTOR_IMAGE: rwuthric/inlfuxdb-connector
```

## Configuration in an OpenFactory device configuration file
A typical example of the `influxdb` section in an OpenFactory device configuration file looks like so:
```
devices:

  dht-001:
    uuid: DHT-001

    agent:
      ...

    influxdb:
      url: ${INFLUXDB_URL}
      organisation: OpenFactory
      token: ${INFLUXDB_TOKEN}
      bucket: ofa_bucket
```
which can be deployed by the OpenFactory deployment tool [ofa.py](../../ofa.py) with the command `ofa device connect-influxdb path/to/device_config.yml`.

The following fields need to be defined in the `influxdb` section:
- `url`: url of the InfluxDB server (taken from the environment variable `INFLUXDB_URL` in the example)
- `organisation`: InfluxDB organisation managing the data bucket
- `token`: InfluxDB token to access the organisation (taken from the environment variable `INFLUXDB_TOKEN` in the example)
- `bucket`: InfluxDB bucket where data will be stored
