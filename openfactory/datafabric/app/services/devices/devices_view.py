"""
DataFabric Devices list view
"""
from flask import render_template, current_app
from flask.views import View
from flask_login import login_required
from openfactory import OpenFactory
from openfactory.exceptions import OFAException
from openfactory.assets import Asset, AssetAttribute


class DevicesList(View):
    """
    Devices list view
    """

    decorators = [login_required]

    def dispatch_request(self):
        ofa = OpenFactory(ksqlClient=current_app.ksql)
        devices = ofa.devices()
        for device in devices:
            try:
                agent = Asset(device.asset_uuid + '-AGENT', ksqlClient=current_app.ksql)
                device.add_attribute('agent_avail',
                                     AssetAttribute(
                                         value=agent.agent_avail.value,
                                         tag='AVAILABILITY',
                                         type='Events'
                                         ))
                device.agent_avail = AssetAttribute(
                                         value=agent.agent_avail.value,
                                         tag='AVAILABILITY',
                                         type='Events'
                                         )
            except (OFAException, AttributeError):
                device.agent_avail = "External"
            producer = Asset(device.asset_uuid + '-PRODUCER', ksqlClient=current_app.ksql)
            device.add_attribute('producer_avail',
                                 AssetAttribute(
                                     value=producer.avail.value,
                                     tag='AVAILABILITY',
                                     type='Events'
                                     ))
            try:
                supervisor = Asset(device.asset_uuid + '-SUPERVISOR', ksqlClient=current_app.ksql)
                device.add_attribute('supervisor_avail',
                                     AssetAttribute(
                                         value=supervisor.avail.value,
                                         tag='AVAILABILITY',
                                         type='Events'
                                         ))
            except (OFAException, AttributeError):
                device.supervisor_avail = ""
        return render_template("services/devices/devices_list.html",
                               devices=devices,
                               title='Devices')
