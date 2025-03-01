"""
DataFabric Devices list view
"""
from flask import render_template
from flask.views import View
from flask_login import login_required
from openfactory import OpenFactory
from openfactory.exceptions import OFAException
from openfactory.assets import Asset


class DevicesList(View):
    """
    Devices list view
    """

    decorators = [login_required]

    def dispatch_request(self):
        ofa = OpenFactory()
        devices = ofa.devices()
        for device in devices:
            try:
                agent = Asset(device.asset_uuid + '-AGENT')
                device.agent_avail = agent.agent_avail
            except (OFAException, AttributeError):
                device.agent_avail = "External"
            producer = Asset(device.asset_uuid + '-PRODUCER')
            device.producer_avail = producer.avail
            try:
                supervisor = Asset(device.asset_uuid + '-SUPERVISOR')
                device.supervisor_avail = supervisor.avail
            except (OFAException, AttributeError):
                device.supervisor_avail = ""
        return render_template("services/devices/devices_list.html",
                               devices=devices,
                               title='Devices')
