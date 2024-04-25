"""
Mocks for AgentKafkaProducer
"""
from unittest.mock import Mock


agent_kafka_producer = Mock()
agent_kafka_producer.send_producer_availability = Mock()
agent_kafka_producer.send_agent_availability = Mock()
