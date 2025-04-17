import os
from openfactory.apps.supervisor import OPCUASupervisor
from openfactory.kafka import KSQLDBClient


"""
OpenFactory Device Command Supervisor using OPC UA to communicate with the device command adapter
"""

supervisor = OPCUASupervisor(
    supervisor_uuid=os.getenv('SUPERVISOR_UUID'),
    device_uuid=os.getenv('DEVICE_UUID'),
    adapter_ip=os.getenv('ADAPTER_IP'),
    adapter_port=os.getenv('ADAPTER_PORT'),
    ksqlClient=KSQLDBClient(os.getenv('KSQLDB_URL')),
    bootstrap_servers=os.getenv('KAFKA_BROKER')
)

supervisor.run()
