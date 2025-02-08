# KSQL Initial Structures  

This folder contains the ksqlDB scripts used to create the initial streams and tables required by OpenFactory.  

## MTCDevice  

The script [mtcdevices.sql](mtcdevices.sql) defines the following ksqlDB streams and tables:  

- **`DEVICES_STREAM`**: A stream containing all Kafka messages from the `mtc_devices` topic, which is used by the Kafka producers of the deployed devices in OpenFactory.  
- **`DEVICES_AVAIL_STREAM`**: A derived stream that selects only the availability entries of devices.  
- **`DEVICES_AVAIL_TOMBSTONES`**: A stream ensuring that any Kafka message in the `mtc_devices` topic (or equivalently in the `DEVICES_STREAM`) with an availability value of `delete` produces a ksqlDB tombstone message (i.e., removes its entry from the topology).  
- **`DEVICES_AVAIL`**: A table listing the availability status of OpenFactory devices.  

### How to Remove a Row in `DEVICES_AVAIL`  

#### Using ksqlDB  

Insert a message into the `DEVICES_STREAM` like this:  

```sql
INSERT INTO devices_stream (device_uuid, id, value)
VALUES ('DEVICE-UUID', 'avail', 'delete');
```

where `DEVICE-UUID` is the UUID of the device whose availability status should be removed from the `DEVICES_AVAIL` table.  

#### Using Python  

Insert a tombstone message into the topic associated with the `DEVICES_AVAIL` table:  

```python
from confluent_kafka import Producer
from pyksql.ksql import KSQL
import openfactory.config as config

device_uuid = 'DEVICE-UUID'
ksql = KSQL(config.KSQLDB)
prod = Producer({'bootstrap.servers': config.KAFKA_BROKER})
prod.produce(topic=ksql.get_kafka_topic('devices_avail'),
             key=device_uuid.encode('utf-8'),
             value=None)
prod.flush()
```  
