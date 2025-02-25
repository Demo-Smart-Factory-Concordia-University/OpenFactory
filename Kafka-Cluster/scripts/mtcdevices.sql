SET 'auto.offset.reset' = 'earliest';

-- MTConnect Devices data stream
CREATE STREAM devices_stream (
        device_uuid VARCHAR KEY,
        id VARCHAR,
        value VARCHAR,
        tag VARCHAR,
        type VARCHAR
    ) WITH (
        KAFKA_TOPIC = 'mtc_devices',
        PARTITIONS = 1,
        VALUE_FORMAT = 'JSON'
    );

-- MTConnect Devices data stream with composite key
CREATE STREAM enriched_devices_stream AS
  SELECT 
    device_uuid,
    id,
    concat(concat(CAST(device_uuid AS STRING), '|'), CAST(id AS STRING)) AS key,
    value,
    type,
    tag
  FROM devices_stream
  PARTITION BY device_uuid;

-- MTConnect Devices data table
CREATE TABLE devices AS
  SELECT 
    key,
    LATEST_BY_OFFSET(device_uuid) AS device_uuid,
    LATEST_BY_OFFSET(id) AS id,
    LATEST_BY_OFFSET(value) AS value,
    LATEST_BY_OFFSET(type) AS type,
    LATEST_BY_OFFSET(tag) AS tag
  FROM enriched_devices_stream
  GROUP BY key;

-- ---------------------------------------------------------------------
-- Docker Swarm services of assets

-- Stream for Docker services of OpenFactory Assets
CREATE STREAM docker_services_stream WITH (
    KAFKA_TOPIC = 'docker_services_topic',
    VALUE_FORMAT = 'JSON',
    PARTITIONS = 1
) AS 
SELECT device_uuid, VALUE AS docker_service
FROM devices_stream 
WHERE ID = 'DockerService' AND TYPE = 'OpenFactory';

-- Table for Docker services of OpenFactory Assets
CREATE SOURCE TABLE docker_services (
    device_uuid VARCHAR PRIMARY KEY,
    docker_service VARCHAR
) WITH (
    KAFKA_TOPIC = 'docker_services_topic',
    VALUE_FORMAT = 'JSON',
    PARTITIONS = 1
);

-- ---------------------------------------------------------------------
-- Assets deployed on OpenFactory cluster 

-- Stream for OpenFactory Assets tombstones
CREATE STREAM assets_tombstones WITH (
    KAFKA_TOPIC = 'assets_topic',
    VALUE_FORMAT = 'KAFKA',
    PARTITIONS = 1
) AS 
SELECT device_uuid, CAST(NULL AS VARCHAR) AS type
FROM devices_stream
WHERE ID = 'AssetType' AND TYPE = 'OpenFactory' AND VALUE = 'delete';

-- Stream for OpenFactory Assets types
CREATE STREAM assets_stream WITH (
    KAFKA_TOPIC = 'assets_topic',
    VALUE_FORMAT = 'JSON',
    PARTITIONS = 1
) AS 
SELECT device_uuid, value AS type
FROM devices_stream 
WHERE ID = 'AssetType' AND TYPE = 'OpenFactory';

-- Table for OpenFactory Assets
CREATE SOURCE TABLE assets (
    device_uuid VARCHAR PRIMARY KEY,
    type VARCHAR
) WITH (
    KAFKA_TOPIC = 'assets_topic',
    VALUE_FORMAT = 'JSON',
    PARTITIONS = 1
);

-- ---------------------------------------------------------------------
-- OpenFactory Assets availability

-- Stream for devices availability tombstones
CREATE STREAM devices_avail_tombstones WITH (
    KAFKA_TOPIC = 'devices_avail_topic',
    VALUE_FORMAT = 'KAFKA',
    PARTITIONS = 1
) AS 
SELECT device_uuid, CAST(NULL AS VARCHAR) AS value
FROM devices_stream
WHERE (id IN ('avail', 'agent_avail') AND value = 'delete');

-- Stream for devices availability
CREATE STREAM devices_avail_stream WITH (
    KAFKA_TOPIC = 'devices_avail_topic',
    VALUE_FORMAT = 'JSON',
    PARTITIONS = 1
) AS 
SELECT device_uuid, value AS availability
FROM devices_stream 
WHERE (id IN ('avail', 'agent_avail') AND value != 'delete');

-- Table for devices availability status
CREATE SOURCE TABLE devices_avail (
    device_uuid VARCHAR PRIMARY KEY,
    availability VARCHAR
) WITH (
    KAFKA_TOPIC = 'devices_avail_topic',
    VALUE_FORMAT = 'JSON',
    PARTITIONS = 1
);
