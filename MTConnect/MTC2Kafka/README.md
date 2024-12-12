# OpenFactory MTConnect producer
Files required to create the Docker image `kafka-mtc-producer`.

The Docker image contains a Kafka producer ingesting MTConnect data from an MTConnect agent.

## Docker image
The GitHub workflow [kafka_mtc_producer.yml](../../.github/workflows/kafka_mtc_producer.yml) creates the Docker image and pushes it to DockerHub. This image is used by OpenFacotry to deploy MTConnect producers for devices. 

The variable `MTCONNECT_PRODUCER_IMAGE` in the OpenFactory configuration file [openfactory.yml](../../openfactory/config/openfactory.yml) points to this image. If the image created from the GitHub workflow is used, this would be:
```
MTCONNECT_PRODUCER_IMAGE: rwuthric/kafka-mtc-producer
```

## Configuration in an OpenFactory device configuration file
A typical example of the `adapter` section in an OpenFactory device configuration file looks like so:
```
devices:

  dht-001:
    uuid: DHT-001

    agent:
      port: 3100
      device_xml: sensors/DHT/dht.xml
      adapter:
        ip: <adapter-ip-address>
        port: 7878

```
which can be deployed by the OpenFactory deployment tool [ofa.py](../../ofa.py) with the command `ofa device up path/to/device_config.yml`.

The following fields need to be defined in the `influxdb` section:
- `ip`: ip address on which the MTConnect adapter is running
- `port`: MTConnect adapter port
