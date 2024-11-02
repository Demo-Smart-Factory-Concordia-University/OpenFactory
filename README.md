# OpenFactory
[![Lint with Flake8](https://github.com/Demo-Smart-Factory-Concordia-University/OpenFactory/actions/workflows/lint.yml/badge.svg)](https://github.com/Demo-Smart-Factory-Concordia-University/OpenFactory/actions/workflows/lint.yml)
[![Unit tests](https://github.com/Demo-Smart-Factory-Concordia-University/OpenFactory/actions/workflows/unittests.yml/badge.svg)](https://github.com/Demo-Smart-Factory-Concordia-University/OpenFactory/actions/workflows/unittests.yml)


Here’s the revised README with more straightforward language and less commercial phrasing:
**OpenFactory** is a distributed cluster designed for seamless integration of manufacturing devices, enabling data to be streamed efficiently to Kafka. It provides an adaptable infrastructure to interface both MTConnect-enabled and retrofitted devices, using adapters when necessary.

## Key Features

- **Device Integration**: Supports both MTConnect-enabled devices directly and non-enabled devices via adapters, providing flexibility in connecting diverse equipment.
- **Data Streaming to Kafka**: Although Kafka itself is not part of *OpenFactory*, the system includes everything needed to prepare, process, and stream device data into a Kafka instance.
- **Microservices Architecture**: Using Docker Swarm, *OpenFactory* orchestrates each microservice independently, allowing for modular, scalable deployments.
- **Infrastructure as Code (IaC)**: Fully configurable via YAML files, *OpenFactory* leverages IaC principles, making it easy to define, version, and deploy infrastructure consistently across environments.
- **Flexible Deployment Options**: Deploy *OpenFactory* on-premises, in the cloud, or in a hybrid configuration to meet operational needs.

## Layered Architecture Overview for Manufacturing Integration

The architecture supporting *OpenFactory* is organized into five distinct layers, with *OpenFactory* taking care of the first three:

1. **Perception Layer**: This foundational layer consists of devices such as sensors and manufacturing equipment that collect data from the physical environment.

2. **Connection Layer**: This layer comprises data connectors that facilitate communication between devices and the system, ensuring seamless data transfer.

3. **Aggregation Layer**: Here, Kafka acts as a storage layer, while ksqlDB serves as a compute layer, enabling the processing and organization of incoming data streams.

4. **Application Layer**: Following data streaming with Kafka sink connectors, various applications can utilize the data for real-time visualization, alarm notifications, data preservation, and machine learning.

5. **Business Layer**: In this top layer, the data is prepared for advanced tasks such as analytics, reporting, visualization, and data mining, enabling organizations to derive actionable insights from their data.

![Data Flow OpenFactory](docs/img/DataFlow.png)

## Architecture

*OpenFactory* employs a microservices architecture orchestrated by Docker Swarm, where various microservices required for device integration are automatically created and deployed based on YAML configurations. Key components include:

- **Adapters**: Facilitate data compatibility for non-MTConnect devices.
- **Agents**: Collect and transmit data from devices to Kafka, ensuring smooth integration and real-time data flow.
- **Kafka**: While not part of *OpenFactory*, it serves as the data stream platform where processed data is sent.
- **ksqlDB**: Provides real-time stream processing, enabling users to query and manipulate data dynamically for actionable insights.
- **Docker Swarm**: Coordinates and manages microservices across the cluster for optimal performance.

## Scalability

*OpenFactory* is built for scalability, enabling the addition of resources as demand grows. Its microservices architecture, managed by Docker Swarm, allows individual services to be scaled independently based on operational needs. This modularity ensures that as more devices are integrated or data processing requirements increase, *OpenFactory* can adapt efficiently, supporting both horizontal and vertical scaling.

## Elasticity

*OpenFactory* exhibits strong elasticity, allowing it to adapt quickly to changing workloads and operational demands. This capability enables the system to allocate resources dynamically, ensuring that microservices can scale up or down based on real-time usage. As the volume of data from devices fluctuates or as processing needs change, *OpenFactory* can efficiently adjust resource allocation, optimizing performance without manual intervention.

## Fault Tolerance

*OpenFactory* is designed with fault tolerance in mind, leveraging Docker Swarm's orchestration capabilities to ensure high availability and resilience. The replication of microservices across multiple nodes allows the system to continue functioning smoothly even if some components fail. This redundancy minimizes downtime and guarantees that data streams remain operational, providing continuous service for device integration and data processing.

## Hybrid Deployment

*OpenFactory* supports hybrid deployment strategies, allowing organizations to combine on-premises resources with cloud-based infrastructure. This flexibility enables businesses to optimize their operations by leveraging the benefits of both environments, such as improved resource utilization and reduced latency for local operations.

## Distributed Architecture

*OpenFactory* operates on a distributed architecture, ensuring that components can be spread across multiple nodes in a network. This distribution enhances performance by allowing parallel processing of data streams and improves reliability through redundancy. By decentralizing resource management and processing, *OpenFactory* can efficiently handle large volumes of data from multiple devices.
