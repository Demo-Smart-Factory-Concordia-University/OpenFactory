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
SELECT * FROM devices_stream 
WHERE (id IN ('avail', 'agent_avail') AND value != 'delete');

-- Table for devices availability status
CREATE SOURCE TABLE devices_avail (
    device_uuid VARCHAR PRIMARY KEY,
    value VARCHAR
) WITH (
    KAFKA_TOPIC = 'devices_avail_topic',
    VALUE_FORMAT = 'JSON',
    PARTITIONS = 1
);
