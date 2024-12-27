"""
DataFabric Device services list view
"""
from openfactory.datafabric.app.services.core.services_list_view import ServicesListView


class DeviceServicesList(ServicesListView):
    """
    Device services list view
    """

    def dispatch_request(self, device_uuid):
        self.device_uuid = device_uuid
        self.service_name = f"Services of device {device_uuid}"
        return super().dispatch_request()

    def filter_services(self, services):
        """
        Filter services
        """
        return [service for service in services if service.name.startswith(self.device_uuid.lower())]
