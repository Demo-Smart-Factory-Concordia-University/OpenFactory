-- OpenFactory cmds stream
CREATE STREAM cmds_stream (
        device_uuid VARCHAR KEY,
        cmd VARCHAR,
        args VARCHAR
    ) WITH (
        KAFKA_TOPIC = 'ofa_cmds',
        PARTITIONS = 1,
        REPLICAS = 1,
        VALUE_FORMAT = 'JSON'
    );
