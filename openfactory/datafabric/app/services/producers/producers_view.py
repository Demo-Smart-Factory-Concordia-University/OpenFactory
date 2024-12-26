"""
DataFabric Producers list view
"""
from openfactory.datafabric.app.services.core.services_list_view import ServicesListView


class ProducersList(ServicesListView):
    """
    Producers list view
    """

    service_name = "Kafka producers"

    def filter_services(self, services):
        """
        Filter services
        """
        return [service for service in services if service.name.endswith('-producer')]
