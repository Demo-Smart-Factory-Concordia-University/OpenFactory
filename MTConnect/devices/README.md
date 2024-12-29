# OpenFactory Device Configuration Files
This folder contains examples of OpenFactory device configuration files and their usage.

## OpenFactory Device Configuration File Structure
An OpenFactory device configuration file follows this structure:

```yaml
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

You can define multiple devices within the `devices` section. Each device must have a unique name (e.g., `device-id` in the example above). The following sections can be configured for each device:

- **`uuid`**: A mandatory field containing the OpenFactory-wide [unique identifier](#device-uuid) for the device.
- **`agent`**: A mandatory section describing how the device's [agent](#agent) collects data.
- **`supervisor`**: An optional section describing how the [supervisor](#supervisor) sends commands to the device.
- **`influxdb`**: An optional section configuring the [InfluxDB connector](#influxdb-connector) for sending data to an InfluxDB database.

### Device UUID
Every device in OpenFactory must be assigned a unique identifier (UUID). This UUID is used across OpenFactory for purposes such as creating ksqlDB streams and tables for data processing.

### Agent Configuration
The `agent` section is mandatory and describes how the device's agent collects data. The configuration depends on whether the device is MTConnect-ready or requires an adapter.

#### MTConnect-Ready Devices
For MTConnect-ready devices, the configuration file follows this structure:

```yaml
devices:
  device-id:
    uuid: <device-uuid>
    agent:
      ip: <agent-ip-address>
      port: <agent-port>
```

The mandatory fields are:
- **`ip`**: The IP address of the MTConnect-ready device.
- **`port`**: The port on which the device's MTConnect agent is running.

**Note:** OpenFactory uses the UUID specified in the configuration file, regardless of the UUID used by the MTConnect-ready device.

#### Devices Requiring an Adapter
For devices that require an adapter, the configuration file follows this structure:

```yaml
devices:
  device-id:
    uuid: <device-uuid>
    agent:
      port: 3000
      device_xml: sensors/DHT/dht.xml
      adapter:
        ip: <adapter-ip-address>
        port: <adapter-port>
      deploy:
        ...
```

The required fields and sections under `agent` are:
- **`port`**: A unique port (OpenFactory-wide) for the deployed agent.
- **`device_xml`**: The location of the MTConnect [device information model](#mtconnect-device-information-model-device_xml).
- **`adapter`**: The [adapter section](#adapter-section-adapter) specifying the adapter's configuration.
- **`deploy`**: An optional [deploy section](#deploy-section-deploy).

##### MTConnect Device Information Model (`device_xml`)
The MTConnect device information model can be specified in the following ways:
- **Local Files**: Use a relative path to the OpenFactory device configuration file, e.g., `relative/path/device.xml`.
- **GitHub Files**: Specify the path as `github://repo@/path/to/device.xml`. For example, `Demo-Smart-Factory-Concordia-University:DemoFactory/devices/models/cnc/ZAIX/zaix-XZ.xml`.

**Note:** When using GitHub files:
- Files in private repositories require a GitHub access token configured in the OpenFactory admin interface.
- The access token must be stored in the `github_access_tokens` configuration variable in the following format:

```json
{
  "repo1": {
    "token": "<github-access-token>",
    "user": "<github-user>"
  },
  "repo2": {
    "token": "<github-access-token>",
    "user": "<github-user>"
  }
}
```

##### Adapter Section (`adapter`)
Adapters can be external or deployed from a Docker image:

- **External Adapter**:
  ```yaml
  adapter:
    ip: <adapter-ip-address>
    port: <adapter-port>
  ```
  - **`ip`**: IP address of the adapter.
  - **`port`**: Port on which the adapter listens.

- **Docker-Image-Based Adapter**:
  ```yaml
  adapter:
    image: <docker-image>
    port: <adapter-port>
    environment:
      - VAR1=value1
      - VAR2=value2
  ```
  - **`image`**: Docker image of the adapter (must on a Docker repository in order each OpenFactory node can pull it).
  - **`port`**: Port on which the adapter listens.
  - **`environment`**: (Optional) List of environment variables for the container.

##### Deploy Section (`deploy`)
The optional `deploy` section specifies service deployment settings in Docker Swarm format:

```yaml
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

- **`replicas`**: Number of service instances (currently not functional in OpenFactory).
- **`resources`**: Resource limits (`cpus`, `memory`) and reservations for deployment.

### Supervisor
Refer to the [Supervisor Documentation](../../openfactory/cmds/) for more details.

### InfluxDB Connector
Refer to the [InfluxDB Connector Documentation](../../InfluxDB/connector/README.md) for more information.