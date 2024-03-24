# OpenFactory
[![Lint with Flake8](https://github.com/Demo-Smart-Factory-Concordia-University/OpenFactory/actions/workflows/lint.yml/badge.svg)](https://github.com/Demo-Smart-Factory-Concordia-University/OpenFactory/actions/workflows/lint.yml)
[![Unit tests](https://github.com/Demo-Smart-Factory-Concordia-University/OpenFactory/actions/workflows/unittests.yml/badge.svg)](https://github.com/Demo-Smart-Factory-Concordia-University/OpenFactory/actions/workflows/unittests.yml)

Framework for manufacturing data management

## How it works
OpenFactory streams relevant data into Kafka topics. On top of Kafka, OpenFactory runs a [ksqlDB](https://ksqldb.io/) server. The ksqlDB server allows to perform data stream processing using a language very similar to standard SQL.

![Data Flow OpenFactory](docs/img/DataFlow.png)
