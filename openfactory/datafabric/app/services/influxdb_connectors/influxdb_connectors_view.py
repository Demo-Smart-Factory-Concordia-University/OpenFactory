"""
DataFabric InlfuxDB connectors list view
"""
from openfactory.datafabric.app.services.core.services_tasks_view import ServicesTasksListView


class InfluxdbConnectorsList(ServicesTasksListView):
    """
    InlfuxDB connectors list view
    """

    service_name = "InfluxDB connectors"

    def filter_services(self, services):
        """
        Filter services
        """
        return [service for service in services if service.name.endswith('-influxdb-connector')]
