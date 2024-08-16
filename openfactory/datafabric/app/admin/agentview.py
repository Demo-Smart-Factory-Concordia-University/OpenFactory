from flask_admin.contrib.sqla import ModelView


class AgentView(ModelView):
    """
    Admin View for Agent Model
    """
    form_columns = ['uuid', 'agent_port', 'node']
    column_list = ['uuid', 'device_uuid', 'device_xml', 'agent_port', 'adapter_ip', 'adapter_port', 'cpus_reservation', 'cpus_limit', 'container', 'node', 'status']
    column_labels = {'uuid': 'Agent UUID',
                     'device_xml': 'Device xml model',
                     'cpus_reservation': 'CPUs reservation',
                     'cpus_limit': 'CPUs limit',
                     'adapter_ip': 'Adapter IP',
                     'device_uuid': 'Device UUID'}
