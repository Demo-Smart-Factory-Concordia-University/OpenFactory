"""
DataFabric Agents list view
"""
from openfactory.datafabric.app.services.core.services_list_view import ServicesListView


class AgentsList(ServicesListView):
    """
    Agents list view
    """

    service_name = "Agents"

    def filter_services(self, services):
        """
        Filter services
        """
        return [service for service in services if service.name.endswith('-agent')]
