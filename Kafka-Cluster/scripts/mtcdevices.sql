SET 'auto.offset.reset' = 'earliest';

-- OpenFactory Assets data stream
CREATE STREAM assets_stream (
        asset_uuid VARCHAR KEY,
        id VARCHAR,
        value VARCHAR,
        tag VARCHAR,
        type VARCHAR,
        attributes MAP<VARCHAR, VARCHAR>
    ) WITH (
        KAFKA_TOPIC = 'ofa_assets',
        PARTITIONS = 1,
        VALUE_FORMAT = 'JSON'
    );

-- OpenFactory Assets data stream with composite key
CREATE STREAM enriched_assets_stream AS
  SELECT 
    asset_uuid,
    id,
    concat(concat(CAST(asset_uuid AS STRING), '|'), CAST(id AS STRING)) AS key,
    value,
    type,
    tag,
    COALESCE(attributes['timestamp'], 'UNAVAILABLE') AS timestamp
  FROM assets_stream
  PARTITION BY asset_uuid;

-- OpenFactory Assets data table
CREATE TABLE assets AS
  SELECT 
    key,
    LATEST_BY_OFFSET(asset_uuid) AS asset_uuid,
    LATEST_BY_OFFSET(id) AS id,
    LATEST_BY_OFFSET(value) AS value,
    LATEST_BY_OFFSET(type) AS type,
    LATEST_BY_OFFSET(tag) AS tag,
    LATEST_BY_OFFSET(timestamp) AS timestamp
  FROM enriched_assets_stream
  GROUP BY key;

-- ---------------------------------------------------------------------
-- Docker Swarm services of assets

-- Stream for Docker services of OpenFactory Assets
CREATE STREAM docker_services_stream WITH (
    KAFKA_TOPIC = 'docker_services_topic',
    VALUE_FORMAT = 'JSON',
    PARTITIONS = 1
) AS 
SELECT asset_uuid, VALUE AS docker_service
FROM assets_stream 
WHERE ID = 'DockerService' AND TYPE = 'OpenFactory';

-- Table for Docker services of OpenFactory Assets
CREATE SOURCE TABLE docker_services (
    asset_uuid VARCHAR PRIMARY KEY,
    docker_service VARCHAR
) WITH (
    KAFKA_TOPIC = 'docker_services_topic',
    VALUE_FORMAT = 'JSON',
    PARTITIONS = 1
);

-- ---------------------------------------------------------------------
-- Assets deployed on OpenFactory cluster 

-- Stream for OpenFactory Assets tombstones
CREATE STREAM assets_type_tombstones WITH (
    KAFKA_TOPIC = 'assets_types_topic',
    VALUE_FORMAT = 'KAFKA',
    PARTITIONS = 1
) AS 
SELECT asset_uuid, CAST(NULL AS VARCHAR) AS type
FROM assets_stream
WHERE ID = 'AssetType' AND TYPE = 'OpenFactory' AND VALUE = 'delete';

-- Stream for OpenFactory Assets types
CREATE STREAM assets_type_stream WITH (
    KAFKA_TOPIC = 'assets_types_topic',
    VALUE_FORMAT = 'JSON',
    PARTITIONS = 1
) AS 
SELECT asset_uuid, value AS type
FROM assets_stream 
WHERE ID = 'AssetType' AND TYPE = 'OpenFactory';

-- Table for OpenFactory Assets
CREATE SOURCE TABLE assets_type (
    asset_uuid VARCHAR PRIMARY KEY,
    type VARCHAR
) WITH (
    KAFKA_TOPIC = 'assets_types_topic',
    VALUE_FORMAT = 'JSON',
    PARTITIONS = 1
);

-- ---------------------------------------------------------------------
-- OpenFactory Assets availability

-- Stream for assets availability tombstones
CREATE STREAM assets_avail_tombstones WITH (
    KAFKA_TOPIC = 'assets_avail_topic',
    VALUE_FORMAT = 'KAFKA',
    PARTITIONS = 1
) AS 
SELECT asset_uuid, CAST(NULL AS VARCHAR) AS value
FROM assets_stream
WHERE (id IN ('avail', 'agent_avail') AND value = 'delete');

-- Stream for assets availability
CREATE STREAM assets_avail_stream WITH (
    KAFKA_TOPIC = 'assets_avail_topic',
    VALUE_FORMAT = 'JSON',
    PARTITIONS = 1
) AS 
SELECT asset_uuid, value AS availability
FROM assets_stream 
WHERE (id IN ('avail', 'agent_avail') AND value != 'delete');

-- Table for assets availability status
CREATE SOURCE TABLE assets_avail (
    asset_uuid VARCHAR PRIMARY KEY,
    availability VARCHAR
) WITH (
    KAFKA_TOPIC = 'assets_avail_topic',
    VALUE_FORMAT = 'JSON',
    PARTITIONS = 1
);
