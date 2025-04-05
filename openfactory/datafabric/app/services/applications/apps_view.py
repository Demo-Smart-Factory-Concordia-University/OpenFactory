"""
DataFabric Applications list view
"""
from flask import current_app
from openfactory import OpenFactory
from openfactory.datafabric.app.services.core.services_list_view import ServicesListView


class ApplicationsList(ServicesListView):
    """
    Applications list view
    """

    service_name = "Applications"

    def filter_services(self):
        """
        Filter services
        """
        ofa = OpenFactory(ksqlClient=current_app.ksql)
        return [app.DockerService.value for app in ofa.applications()]
