def murmur2(data):
    """
    Kafka's Murmur2 hashing implementation, ported to Python
    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    length = len(data)
    seed = 0x9747b28c
    m = 0x5bd1e995
    r = 24

    h = seed ^ length
    length4 = length // 4

    for i in range(length4):
        i4 = i * 4
        k = (
            (data[i4 + 0] & 0xff)
            | ((data[i4 + 1] & 0xff) << 8)
            | ((data[i4 + 2] & 0xff) << 16)
            | ((data[i4 + 3] & 0xff) << 24)
        )
        k = (k * m) & 0xFFFFFFFF
        k ^= (k >> r) & 0xFFFFFFFF
        k = (k * m) & 0xFFFFFFFF
        h = (h * m) & 0xFFFFFFFF
        h ^= k & 0xFFFFFFFF

    extra_bytes = length % 4
    if extra_bytes == 3:
        h ^= (data[-1] & 0xff) << 16
        h ^= (data[-2] & 0xff) << 8
        h ^= (data[-3] & 0xff)
    elif extra_bytes == 2:
        h ^= (data[-1] & 0xff) << 8
        h ^= (data[-2] & 0xff)
    elif extra_bytes == 1:
        h ^= (data[-1] & 0xff)
    if extra_bytes:
        h = (h * m) & 0xFFFFFFFF

    h ^= (h >> 13) & 0xFFFFFFFF
    h = (h * m) & 0xFFFFFFFF
    h ^= (h >> 15) & 0xFFFFFFFF

    return h


def get_partition_for_key(key, num_partitions):
    """ Calculate the partition number for a given key using Kafka's default partitioning strategy """
    hash_val = murmur2(key)
    return (hash_val & 0x7FFFFFFF) % num_partitions
