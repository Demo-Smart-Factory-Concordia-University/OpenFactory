# Kafka Cluster
Docker compose instructions to wire up a standalone [Kafka](https://kafka.apache.org/) server together with a [ksqlDB](https://ksqldb.io/) server.

The Docker container exports port `9092` to give access the Kafka standalone server from the host running the container.

## Build Docker Image
To build the Docker image, it is required that the SSH key to authentify with GitHub is stored in `~/.ssh/id_ed25519` on your Docker host.

To build the Docker image use
```
docker compose build
```

## Run the Kafka Cluster
Wire up a Docker container with
```
docker compose up -d
```

## Attaching the Kafka Cluster to other micro-services
Services running in other Docker containers need to connect to the Kafka cluster over `broker:29092` and attach the `factory-net` network like so in their `docker-compose.yml`:

In the networks section:
```
networks:

  factory-net:
    name: factory-net
    driver: overlay
    external: true
```

In the services:
```
services:

  my-service:
    ...
    networks:
      - factory-net
```

## Health check
The `docker-compose.yml` contains a `healthcheck` section. This allows to wire up the cluster like so:
```
docker compose up --wait
```
to make sure that container is not only up but healthy as well (broker is ready to obtain messages). Note that this will automatically wire up the container in detached mode.

## Querying Kafka ksqlDB
To launch `ksql`, ksqlDB's interactive CLI interface, run:
```
docker exec -it ksqldb-cli ksql http://ksqldb-server:8088
```
This will launch `ksql` running in the `ksqldb-cli` Docker container.

To list all kafka topics, run in `ksql`:
```
ksql> list topics;
```
To follow all the messages from a topic, for example the `mmp_services` topic:
```
ksql> print mmp_services from beginning;
```
To quit `ksql` and the `ksqldb-cli` container:
```
ksql> exit
```

