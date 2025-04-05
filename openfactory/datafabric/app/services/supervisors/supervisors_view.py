"""
DataFabric Supervisors list view
"""
from flask import current_app
from openfactory import OpenFactory
from openfactory.datafabric.app.services.core.services_list_view import ServicesListView


class SupervisorsList(ServicesListView):
    """
    Supervisors list view
    """

    service_name = "Supervisors"

    def filter_services(self):
        """
        Filter services
        """
        ofa = OpenFactory(ksqlClient=current_app.ksql)
        return [app.DockerService.value for app in ofa.supervisors()]
