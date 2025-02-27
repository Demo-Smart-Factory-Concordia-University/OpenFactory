"""
DataFabric Device services list view
"""
from flask import render_template
from openfactory.datafabric.app.services.core.services_list_view import ServicesListView
from openfactory.assets import Asset
from openfactory.exceptions import OFAException


class DeviceServicesList(ServicesListView):
    """
    Device services list view
    """

    template_name = "services/devices/device_services.html"

    def filter_services(self, services):
        """
        Filter services
        """
        return [service for service in services if service.name.startswith(self.device_uuid.lower())]

    def fetch_data(self, device_uuid):
        """ Fetch data from devices table `"""
        try:
            device = Asset(device_uuid)
            json_result = {
                "Samples": device.samples(),
                "Events": device.events(),
                "Conditions": device.conditions(),
                "Methods": device.methods(),
            }
        except OFAException:
            json_result = {
                "Samples": {},
                "Events": {},
                "Conditions": []
            }
        return json_result

    def dispatch_request(self, device_uuid):
        self.device_uuid = device_uuid
        return render_template(self.template_name,
                               services=self.fetch_service_list(),
                               data=self.fetch_data(device_uuid),
                               title=device_uuid)
