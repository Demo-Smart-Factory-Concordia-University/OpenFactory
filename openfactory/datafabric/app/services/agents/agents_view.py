"""
DataFabric Agents list view
"""
from openfactory import OpenFactory
from openfactory.datafabric.app.services.core.services_list_view import ServicesListView


class AgentsList(ServicesListView):
    """
    Agents list view
    """

    service_name = "Agents"

    def filter_services(self):
        """
        Filter services
        """
        ofa = OpenFactory()
        return [app.DockerService.value for app in ofa.agents()]
