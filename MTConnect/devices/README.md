# OpenFactory Device files
This folder contains examples of OpenFactory device configuration files.

## OpenFactory device configuration file
An OpenFactory device configuration file supports so far this structure:
```
devices:

  device-id:
     uuid: <device-uuid>
     agent:
       ...
     supervisor:
       ...
     influxdb:
       ...
```
As many devices as desired can be defined within the `devices` section. 
Each device will have a unique (unique for the configuration file) name (in the above example `device-id`). In each device section can be defined:
- `uuid`: mandatory field containing the OpenFactory wide [unique identifier](#device-uuid) of the device
- `agent`: mandatory section describing how the device [agent](#agent) is configured to collect the data from the device
- `supervisor`: optional section describing how the device [supervisor](#supervisor) is configured to send commands to the device
- `influxdb`: optional section describing the configuration of the device [InfluxDB connector](#influxdb-connector) to send data to an InfluxDB data base

### Device UUID
Each device in OpenFactory needs to be assigned a unique identifier. This UUID is used to refer in a unique way to the device. For example, it is used to create various ksqlDB streams and tables for data stream processing.

### Agent
The mandatory `agent` section descries how the device agent is configured to collect the data from the device. It can be configured either for MTConect ready devices or for devices requiring and adapter to collect the data

#### MTConnect ready devices
For MTConect ready devices the device configuration file will be:
```
devices:

  dht-ext:
    uuid: DHT-EXT
    agent:
      ip: <agent-ip-address>
      port: <agent-port>
```
where the two mandatory fields within the `agent` section are:
- `ip`: the IP address of the MTConnect ready device
- `port`: the port on which the MTConnect agent of the device is running

OpenFactory will use the UUID defined in the device configuration file regardless on which UUID the MTConnect ready device may be using.

#### Devices requiring an adapter
For devices requiring an adapter to collect data the device configuration file will be:
```
devices:

  dht-001:
    uuid: DHT-001
    agent:
      port: 3000
      device_xml: sensors/DHT/dht.xml
      adapter:
        ip: <adapter-ip-address>
        port: <adapter-port>
      deploy:
        ...
```
where following fields and sections need to be defined within the `agent` section of the device:
- `port`: the unique port (OpenFactory wide) on which the deployed agent will run
- `device_xml`: the location of the MTConnect [device information model](#mtconnect-device-information-model-device_xml)
- `adapter`: the [adapter section](#adapter-section-adapter) describing where the adapter is running
- `deploy`: an optional [deploy section](#deploy-section-deploy)

##### MTConnect device information model (`device_xml`)
The location of the MTConnect device information model can be specified in one of the following ways:
- **local files** : locally stored files can be specified with `relative/path/to/device_xml.xml` by using the path relative to the device configuration file
- **GitHub stored files** : files stored in a GitHub repository can be refered as `github://repo@/path/to/device_.xml` where `repo` is the GitHub repo (e.g. `Demo-Smart-Factory-Concordia-University:DemoFactory`) and the full path of the device information model within this repo (e.g. `/devices/models/cnc/ZAIX/zaix-XZ.xml`)

When using GitHub stored files, they need either to be in a public repository or, if in a private repository, a GitHub access token needs to be defin in the admin section of the OpenFactory web application. The access token has to be stored in the configuration variable `github_access_tokens` following this format:
```
{
    "repo1": 
    {
       "token": "<github-access-token>",
       "user": "<github-user>"
    },
    "repo2": 
    {
       "token": "<github-access-token>",
       "user": "<github-user>"
    }
}

```
As many repositories as desired can be configured where the syntax is like so `Demo-Smart-Factory-Concordia-University:DemoFactory`.

The GitHub access token has to be configured in GitHub at the organisation level of the repository (personal access token - classics) for the GitHub user defined in the `github_access_tokens` configuration variable.

##### Adapter section (`adapter`)
The adapter section can be defined either for an external running adapter:
```
adapter:
ip: <adapter-ip-address>
port: <adapter-port>
```
where `ip` is the IP address where the adapter is running and `port` the port on which it listens, or for an adapter deployed from a Docker image:
```
adapter:
    image: <docker-image>
    port: <adapter-port>
    environment:
        - MY_VAR1=val1
        - MY_VAR2=val2
```
where `image` is a Docker image of the adapter (needs to be on DockerHub in order OpenFactory can deploy it to any OpenFactory node), `port` is the port on which the adapter will listen and `environment` is an optional section listing environment variable passed to the deployed adapter container.

##### Deploy section (`deploy`)
In the optional `deploy` section instructions for the deployment of the services can be specified in the same format as in Docker Swarm:
```
deploy:
    replicas: 1
    resources:
        limits:
        cpus: 1.0
        memory: '1024M'
        reservations:
        cpus: 0.5
        memory: '256M'
```
with
- `replicas`: how many replications of the service (currently has no effect)
- `limits` and `reservations`: specifications on maximal required resources (`cpus` and `memory`) and minimal requried ressources (`cpus` and `memory`)


## Supervisor
More information is available [here](../../openfactory/cmds/)


## InfluxDB connector
More information is available [here](../../InfluxDB/connector/README.md)
