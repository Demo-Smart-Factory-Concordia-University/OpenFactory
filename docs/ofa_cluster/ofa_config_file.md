# OpenFactory Configuration File

The OpenFactory configuration file, [openfactory.yml](../../openfactory/config/openfactory.yml), contains all the settings required for OpenFactory to operate the cluster effectively.

---

## Configurations

### Cluster Nodes Configuration

#### OpenFactory User

A common user account must be set up across all OpenFactory nodes with the following requirements:  
- The account must exist on all nodes.  
- The user must have permission to use Docker.  
- Passwordless SSH key authentication must be configured between the OpenFactory machine and all nodes under this account.  

Refer to the setup guides for detailed instructions:  
- [Manager Nodes](../ofa_cluster/ofa_manager_node_setup.md)  
- [Worker Nodes](../ofa_cluster/ofa_worker_node_setup.md)

```yaml
OPENFACTORY_USER: openfactory
```

#### OpenFactory Manager Node

Defines the IP address of the OpenFactory manager machine. In the example belwo, the IP address is sourced from the environment variable `MANAGER_NODE_IP`.

```yaml
OPENFACTORY_MANAGER_NODE: ${MANAGER_NODE_IP}
```

#### OpenFactory Overlay Network

Specifies the name of the virtual network used within the cluster. OpenFactory automatically creates this network during the initialization process.

```yaml
OPENFACTORY_NETWORK: factory-net
```

---

### OpenFactory Database

OpenFactory uses [SQLAlchemy](https://www.sqlalchemy.org/) to connect to its database. The `SQL_ALCHEMY_CONN` variable contains the SQLAlchemy connection string to access the database (e.g., `sqlite:///local/openfact.db`).

```yaml
SQL_ALCHEMY_CONN: ${SQL_ALCHEMY_CONN}
```

---

### Kafka Cluster Connections

#### Kafka Cluster Broker

Specifies a single broker from the Kafka cluster (currently, only one broker is supported; future versions will allow a list of brokers). In the example below, the broker's IP address is sourced from the environment variable `KAFKA_BROKER`.

```yaml
KAFKA_BROKER: ${KAFKA_BROKER}
```

#### ksqlDB Server

Defines the URL of the ksqlDB server connected to the Kafka cluster.

```yaml
KSQLDB_URL: http://ksqldb-server:8088
```

---

### Docker Images

Docker images for the services running within the cluster are listed below.

#### MTConnect Agent

OpenFactory uses the official [MTConnect C++ Agent](https://github.com/mtconnect/cppagent) from the [MTConnect Institute](https://github.com/mtconnect) to collect data from OpenFactory devices.  

The workflow [mtc_agent.yml](../../.github/workflows/mtc_agent.yml) in this repository builds the image required by OpenFactory.

```yaml
MTCONNECT_AGENT_IMAGE: ghcr.io/demo-smart-factory-concordia-university/mtcagent
MTCONNECT_AGENT_CFG_FILE: ${MTCONNECT_AGENT_CFG_FILE}
```

`MTCONNECT_AGENT_CFG_FILE` must point to the MTConnect Agent configuration file [agent.cfg](../../openfactory/ofa/agent/configs/agent.cfg), which OpenFactory will copy to the container during deployment.

#### Kafka Producer

The Docker image for the Kafka producer, which streams data collected by the agents to Kafka, is built using the workflow [kafka_mtc_producer.yml](../../.github/workflows/kafka_mtc_producer.yml) in this repository.  

This producer uses [python-mtc2kafka](https://github.com/rwuthric/python-mtc2kafka) to source MTConnect data streams from the agent and publish them to Kafka.

```yaml
MTCONNECT_PRODUCER_IMAGE: ghcr.io/demo-smart-factory-concordia-university/kafka-mtc-producer
```
