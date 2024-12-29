# OpenFactory InfluxDB Connector
This folder contains the code for the OpenFactory InfluxDB connector.

## Docker Image
The GitHub workflow [influxdb_connector.yml](../../.github/workflows/influxdb_connector.yml) builds the Docker image and pushes it to DockerHub. This image is utilized by OpenFactory to deploy InfluxDB connectors for devices.

The `INFLUXDB_CONNECTOR_IMAGE` variable in the OpenFactory configuration file [openfactory.yml](../../openfactory/config/openfactory.yml) specifies the location of this image. For instance, if using the image built by the GitHub workflow, the configuration would look like this:

```yaml
INFLUXDB_CONNECTOR_IMAGE: ghcr.io/demo-smart-factory-concordia-university/influxdb_connector:latest
```

## Configuration in an OpenFactory Device Configuration File
Below is an example of the `influxdb` section in an OpenFactory device configuration file:

```yaml
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

This configuration can be deployed using the OpenFactory deployment tool [ofa.py](../../ofa.py) with the following command:

```bash
ofa device connect-influxdb path/to/device_config.yml
```

### Required Fields in the `influxdb` Section:

- **`url`**: The URL of the InfluxDB server (referenced as `${INFLUXDB_URL}` in the example).
- **`organisation`**: The name of the InfluxDB organization managing the data bucket.
- **`token`**: The authentication token for accessing the organization (referenced as `${INFLUXDB_TOKEN}` in the example).
- **`bucket`**: The name of the InfluxDB bucket where the data will be stored.
