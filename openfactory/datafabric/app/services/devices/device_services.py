"""
DataFabric Device services list view
"""
import asyncio
from flask import render_template
from openfactory.datafabric.app.services.core.services_list_view import ServicesListView
from openfactory.datafabric.app import ksql


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
        query = f"SELECT ID, VALUE, TYPE, TAG FROM devices WHERE DEVICE_UUID='{device_uuid.upper()}';"
        df = asyncio.run(ksql.query_to_dataframe(query))
        if not df.empty:
            json_result = {
                "Samples": {row.ID: row.VALUE for row in df[df["TYPE"] == "Samples"].itertuples()},
                "Events": {row.ID: row.VALUE for row in df[df["TYPE"] == "Events"].itertuples()},
                "Conditions": [
                    {
                        "ID": row.ID,
                        "VALUE": None if str(row.TAG).lower() == "unavailable" else row.VALUE,
                        "TAG": row.TAG
                    }
                    for row in df[df["TYPE"] == "Condition"].itertuples()
                ]
            }
        else:
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
