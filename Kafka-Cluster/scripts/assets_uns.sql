-- ---------------------------------------------------------------------
-- Mapping between ASSET_UUID and UNS_ID

-- Source table for mapping between asset_uuid and uns_id
CREATE TABLE asset_to_uns_map_raw (
    asset_uuid VARCHAR PRIMARY KEY,
    uns_id VARCHAR,
    updated_at TIMESTAMP
) WITH (
    KAFKA_TOPIC = 'asset_to_uns_map_topic',
    KEY_FORMAT = 'KAFKA',
    VALUE_FORMAT = 'JSON',
    PARTITIONS = 1
);

-- Materialized table for querying and joining
CREATE TABLE asset_to_uns_map AS
SELECT * FROM asset_to_uns_map_raw EMIT CHANGES;


-- ---------------------------------------------------------------------
-- OpenFactory Assets data stream keyed by uns_id

-- Create assets_stream_uns
CREATE STREAM assets_stream_uns (
    uns_id VARCHAR KEY,
    asset_uuid VARCHAR,
    id VARCHAR,
    value VARCHAR,
    tag VARCHAR,
    type VARCHAR,
    attributes MAP<VARCHAR, VARCHAR>
) WITH (
    KAFKA_TOPIC = 'ofa_assets_uns',
    VALUE_FORMAT = 'JSON',
    PARTITIONS = 1
);

-- Populate assets_stream_uns with data keyed by UNS_ID
INSERT INTO assets_stream_uns
SELECT
    m.uns_id AS uns_id,
    a.asset_uuid AS asset_uuid,
    a.id,
    a.value,
    a.tag,
    a.type,
    a.attributes
FROM assets_stream a
LEFT JOIN asset_to_uns_map m
    ON a.asset_uuid = m.asset_uuid
WHERE m.uns_id IS NOT NULL
PARTITION BY m.uns_id;


-- ---------------------------------------------------------------------
-- OpenFactory assets data table keyed by uns_id

CREATE TABLE assets_uns AS
SELECT
  concat(m.uns_id, '|', a.id) AS key,  -- new composite key with uns_id (will become table key)
  a.key AS asset_uuid_key,
  m.uns_id AS uns_id,
  a.asset_uuid AS asset_uuid,
  a.id AS id,
  a.value AS value,
  a.type AS type,
  a.tag AS tag,
  a.timestamp AS timestamp
FROM assets a
LEFT JOIN asset_to_uns_map m
  ON a.asset_uuid = m.asset_uuid
WHERE m.uns_id IS NOT NULL;
