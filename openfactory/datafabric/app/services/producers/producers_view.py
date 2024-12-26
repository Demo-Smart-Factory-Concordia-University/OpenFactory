"""
DataFabric Producers list view
"""
from openfactory.datafabric.app.services.core.services_tasks_view import ServicesTasksListView


class ProducersList(ServicesTasksListView):
    """
    Producers list view
    """

    service_name = "Kafka producers"

    def filter_services(self, services):
        """
        Filter services
        """
        return [service for service in services if service.name.endswith('-producer')]
