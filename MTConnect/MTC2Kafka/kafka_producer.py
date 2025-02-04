import os
import signal
from mtc2kafka.connectors import MTCSourceConnector


class MTC_Producer(MTCSourceConnector):
    """ Kafka producer for MTConnect data """

    bootstrap_servers = [os.environ.get('KAFKA_BROKER', os.environ['KAFKA_BROKER'])]
    mtc_agent = os.environ['MTC_AGENT']
    kafka_producer_uuid = os.environ['KAFKA_PRODUCER_UUID']


def signal_handler(sig, frame):
    """ Handles shutdown of producer """
    print(f"Received signal {sig}; cleaning-up ...")
    con.send_producer_availability("UNAVAILABLE")
    exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Setup producer
con = MTC_Producer()
print("======================================================")
print("Kafka producer for MTConnect data from", con.mtc_agent)
print("Streaming from", con.get_agent_baseUrl())
print("======================================================")
print(con.get_agent_instanceId())
print(con.get_latest_stored_agent_instance())
con.stream_mtc_dataItems_to_Kafka(verbose=True)
