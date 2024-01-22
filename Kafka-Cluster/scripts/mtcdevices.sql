-- MTConnect Devices data streams and tables
CREATE STREAM devices_stream (
        device_uuid VARCHAR KEY,
        id VARCHAR,
        value VARCHAR
    ) WITH (
        KAFKA_TOPIC = 'mtc_devices',
        PARTITIONS = 1,
        VALUE_FORMAT = 'JSON'
    );

CREATE TABLE devices_avail AS
    SELECT device_uuid,
           LATEST_BY_OFFSET(value) AS availability
    FROM devices_stream
    WHERE ID='avail' OR ID='agent_avail'
    GROUP BY device_uuid;
