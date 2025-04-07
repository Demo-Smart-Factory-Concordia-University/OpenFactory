# Kafka Partition Hash Testing with Java and Python

This guide will walk you through testing Kafka’s partition hash behavior in Python by running a Java program that computes partition values the same way Kafka does. This is helpful for verifying that the `get_partition_for_key()` function behaves exactly like Kafka’s internal partitioning mechanism.

---

## Prerequisites

1. **Java 8 or later** installed on your machine.
2. **Python** installed (for later testing).
3. **Kafka Clients JAR (version 3.7.0)** and **SLF4J JAR**.

---

## Step 1: Setup Java Project

### 1.1 Clone or Create a Directory

Create a folder for the Java code:

```bash
mkdir kafka-partition-test
cd kafka-partition-test
```

### 1.2 Download Kafka Clients JAR

This is required to access Kafka’s `Utils` class (used for murmur2 hashing).

Download Kafka clients:

```bash
mkdir libs
cd libs
curl -O https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.7.0/kafka-clients-3.7.0.jar
cd ..
```

### 1.3 Download SLF4J JAR

Kafka needs SLF4J for logging. Download the SLF4J API:

```bash
cd libs
curl -O https://repo1.maven.org/maven2/org/slf4j/slf4j-api/2.0.9/slf4j-api-2.0.9.jar
cd ..
```

---

## Step 2: Write Java Code

Create a file named `KafkaPartitionHash.java` in the `kafka-partition-test` folder and add the following code:

```java
import org.apache.kafka.common.utils.Utils;

public class KafkaPartitionHash {
    public static void main(String[] args) {
        String[] keys = {"banana", "apple", "carrot", "", "A", "Zebra"};
        int partitions = 10;

        for (String key : keys) {
            int hash = Utils.toPositive(Utils.murmur2(key.getBytes()));
            int partition = hash % partitions;
            System.out.println("Key: " + key + " => Partition: " + partition);
        }
    }
}
```

---

## Step 3: Compile the Java Code

From the `kafka-partition-test` folder, compile the Java file:

```bash
javac -cp libs/kafka-clients-3.7.0.jar KafkaPartitionHash.java
```

This will generate a `KafkaPartitionHash.class` file.

---

## Step 4: Run the Java Program

To run the program and calculate the Kafka partition hashes for given keys:

- On **Linux/macOS**:

```bash
java -cp .:libs/* KafkaPartitionHash
```

- On **Windows**:

```bash
java -cp ".;libs/*" KafkaPartitionHash
```

This will print output like the following (depending on the partition count):

```
Key: banana => Partition: 7
Key: apple => Partition: 4
Key: carrot => Partition: 3
Key:  => Partition: 5
Key: A => Partition: 9
Key: Zebra => Partition: 8
```

---

## Step 5: Add Java Results to Python Unit Tests

Now, you can use the partition results in your Python tests. The Python function `get_partition_for_key()` should match the output of Kafka’s partition calculation.

### Example Python Test:

Assume the following function in your Python code:

```python
def get_partition_for_key(key, num_partitions):
    # Your murmur2 hashing implementation
    return int(hashlib.md5(key.encode('utf-8')).hexdigest(), 16) % num_partitions
```

Here’s how to write tests:

```python
import unittest
from your_module import get_partition_for_key  # Import your function

class TestKafkaPartitioning(unittest.TestCase):
    def test_kafka_partition_match(self):
        self.assertEqual(get_partition_for_key("banana", 10), 7)
        self.assertEqual(get_partition_for_key("apple", 10), 4)
        self.assertEqual(get_partition_for_key("carrot", 10), 3)
        self.assertEqual(get_partition_for_key("", 10), 5)
        self.assertEqual(get_partition_for_key("A", 10), 9)
        self.assertEqual(get_partition_for_key("Zebra", 10), 8)
```

---

## Step 6: Run Your Python Tests

If you have `pytest` or `unittest` installed, run your tests:

```bash
pytest  # or python -m unittest discover
```

The tests should pass if your Python function behaves exactly like Kafka’s partitioning mechanism.
