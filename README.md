# OpenFactory
[![Lint with Flake8](https://github.com/Demo-Smart-Factory-Concordia-University/OpenFactory/actions/workflows/lint.yml/badge.svg)](https://github.com/Demo-Smart-Factory-Concordia-University/OpenFactory/actions/workflows/lint.yml)
[![Unit tests](https://github.com/Demo-Smart-Factory-Concordia-University/OpenFactory/actions/workflows/unittests.yml/badge.svg)](https://github.com/Demo-Smart-Factory-Concordia-University/OpenFactory/actions/workflows/unittests.yml)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen)](https://openfactory-doc.readthedocs.io/en/latest/index.html)


## What is OpenFactory?

> **OpenFactory** is a deployment and coordination platform for the physical world.
>
> It brings DevOps thinking to manufacturing — making the real world **versionable**, **testable**, **programmable**, and **connected at scale**.

It is designed for large-scale, low-latency coordination, with the goal of managing thousands of assets and handling millions of events per second through Kafka-powered data pipelines.

👉 [Read the full OpenFactory Manifesto](docs/MANIFESTO.md)

## Key Features

- **Device Integration**: Supports both [MTConnect](http://mtconnect.org)-enabled devices directly and non-enabled devices via adapters, providing flexibility in connecting diverse equipment.
- **Data Streaming to Kafka**: Although Kafka itself is not part of *OpenFactory*, the system includes everything needed to prepare, process, and stream device data into a Kafka instance.
- **Microservices Architecture**: Using Docker Swarm, *OpenFactory* orchestrates each microservice independently, allowing for modular, scalable deployments.
- **Infrastructure as Code (IaC)**: Fully configurable via YAML files, *OpenFactory* leverages IaC principles, making it easy to define, version, and deploy infrastructure consistently across environments.
- **Flexible Deployment Options**: Deploy *OpenFactory* on-premises, in the cloud, or in a hybrid configuration to meet operational needs.

## Overview

**OpenFactory** aims to streamline the integration of manufacturing devices into a cohesive data processing ecosystem, enabling efficient data streaming to Kafka for analysis and decision-making, and sending back commands to devices to execute actionable items.

It is a distributed cluster designed for seamless integration of manufacturing devices, providing an adaptable infrastructure to interface both MTConnect-enabled and retrofitted devices using adapters when necessary.

![Data Flow OpenFactory](docs_md/img/DataFlow.png)
The architecture supporting *OpenFactory* is organized into five distinct layers, with *OpenFactory* taking care of the first three:

1. **Perception Layer**: This foundational layer consists of devices such as sensors and manufacturing equipment that collect data from and send commands to the physical environment.

2. **Connection Layer**: This layer comprises data connectors that facilitate communication between devices and the system, ensuring seamless data transfer.

3. **Aggregation Layer**: Here, Kafka acts as a storage layer, while ksqlDB serves as a compute layer, enabling the processing and organization of incoming data streams.

4. **Application Layer**: Following data streaming with Kafka sink connectors, various applications can utilize the data for real-time visualization, alarm notifications, data preservation, and machine learning.

5. **Business Layer**: In this top layer, the data is prepared for advanced tasks such as analytics, reporting, visualization, and data mining, enabling organizations to derive actionable insights from their data.

## Documentation
:books: Documentation: https://openfactory-doc.readthedocs.io/en/latest/index.html

## Architecture

![Data Flow OpenFactory](docs_md/img/OFAArchitecture.png)
*OpenFactory* employs a microservices architecture orchestrated by Docker Swarm, where various microservices required for device integration are automatically created and deployed based on YAML configurations. Key components include:

- **Adapters**: Facilitate data and commands compatibility between devices.
- **Agents**: Collect and transmit data from devices to Kafka, ensuring smooth integration and real-time data flow.
- **Supervisors**: Send commands from Kafka to devices.
- **Kafka**: While not part of *OpenFactory*, it serves as the data stream platform where processed data is sent.
- **ksqlDB**: Provides real-time stream processing, enabling users to query and manipulate data dynamically for actionable insights.
- **Docker Swarm**: Coordinates and manages microservices across the cluster for optimal performance.

A detailed description of the OpenFactory architecture can be found [here](./docs_md/architecture/architecture.md).

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

## Alignment with RAMI 4.0

OpenFactory follows the principles of the [RAMI 4.0 framework](https://www.sci40.com/english/thematic-fields/rami4-0/) through its structured architecture, integrating devices within a digital manufacturing environment. The following outlines how OpenFactory relates to the three axes of RAMI 4.0: Layers, Value Stream, and Lifecycle.

### Layers
OpenFactory adheres to the RAMI 4.0 framework by integrating its functionality across the following layers, ensuring comprehensive data management and processing within a manufacturing context:
- **Asset Layer**: OpenFactory integrates various devices and sensors, forming the basis of the perception layer essential for data collection.
- **Integration Layer**: The connection layer facilitates communication between diverse devices, ensuring seamless data exchange.
- **Communication Layer**: Data streaming via Kafka adheres to standardized communication principles, enhancing interoperability.
- **Information Layer**: Real-time processing with ksqlDB provides actionable insights, transforming collected data into useful information.
- **Business Layer**: The application layer supports analytics and reporting, driving data-informed decision-making and operational efficiency.

### Value Stream
OpenFactory addresses the Value Stream axis of RAMI 4.0 by enabling the seamless flow of data from manufacturing devices into Kafka, allowing for real-time processing and analysis. This infrastructure transforms raw data into actionable insights that drive efficiency and informed decision-making. The microservices architecture supports various applications that utilize this data for analytics, reporting, and machine learning, ensuring that valuable information contributes to optimizing processes within the manufacturing environment. By leveraging Infrastructure as Code (IaC) and offering hybrid deployment options, OpenFactory enhances interoperability and efficiency, contributing to the goals of Industry 4.0.

### Lifecycle
OpenFactory provides the necessary foundation to contribute to effective lifecycle management by enabling coherent data collection and organization. This capability allows relevant information to be stored and accessed, facilitating insights that optimize asset performance throughout their lifecycle.

## License
![License: Polyform Noncommercial](https://img.shields.io/badge/license-Polyform--NC-blue)

This project is licensed under the [Polyform Noncommercial License 1.0.0](LICENSE), effective from release **v0.2.0**.

### **Non-Commercial Use**
Use, modification, and distribution of this software are permitted for **academic, research, and personal purposes**, provided that such use is **non-commercial** in nature.

### **Commercial Use**
Commercial use—including use in any paid product, service, or Software-as-a-Service (SaaS) offering—**requires a separate commercial license**. Interested parties must contact the project maintainer to obtain explicit written permission. Licensing discussions and agreements are managed in coordination with the Concorida Univerity technology transfer office.

For licensing inquiries, please contact: [rolf.wuthrich@concordia.ca]

### **Previous License (v0.1.1 and earlier)**
Versions up to and including **v0.1.1** were released under the **BSD-3-Clause License**. That license remains applicable solely to those earlier versions.

## Contributing

Contributions are welcome under the terms of the **Polyform Noncommercial License**. 

Please note:
- Contributions must align with the project's **non-commercial licensing model**.
- Organizations or individuals intending to use the project in **commercial contexts** must initiate a licensing discussion prior to contributing code.

For guidelines on contributing, refer to [CONTRIBUTING.md](CONTRIBUTING.md).
