"""
DataFabric Producers list view
"""
from openfactory import OpenFactory
from openfactory.datafabric.app.services.core.services_list_view import ServicesListView


class ProducersList(ServicesListView):
    """
    Producers list view
    """

    service_name = "Kafka producers"

    def filter_services(self):
        """
        Filter services
        """
        ofa = OpenFactory()
        return [app.DockerService.value for app in ofa.producers()]
