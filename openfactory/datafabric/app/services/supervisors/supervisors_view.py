"""
DataFabric Supervisors list view
"""
from openfactory.datafabric.app.services.core.services_tasks_view import ServicesTasksListView


class SupervisorsList(ServicesTasksListView):
    """
    Supervisors list view
    """

    service_name = "Supervisors"

    def filter_services(self, services):
        """
        Filter services
        """
        return [service for service in services if service.name.endswith('-supervisor')]
