import os
from mtc2kafka.connectors import MTCSourceConnector


class MTCDHT_Connector(MTCSourceConnector):
    """ Kafka producer for MTConnect data """

    bootstrap_servers = [os.environ.get('KAFKA_BROKER', 'broker:29092')]
    mtc_namespace = os.environ.get('MTC_NAMESPACE', 'urn:mtconnect.org:MTConnectStreams:2.0')
    mtc_agent = os.environ['MTC_AGENT']
    kafka_producer_uuid = os.environ['KAFKA_PRODUCER_UUID']


con = MTCDHT_Connector()
print("======================================================")
print("Kafka producer for MTConnect data from", con.mtc_agent)
print("Streaming from", con.get_agent_baseUrl())
print("======================================================")
print(con.get_agent_instanceId())
print(con.get_latest_stored_agent_instance())
con.stream_mtc_dataItems_to_Kafka(verbose=True)
