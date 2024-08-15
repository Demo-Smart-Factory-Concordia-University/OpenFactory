from flask_admin.contrib.sqla import ModelView


class AgentView(ModelView):
    """
    Admin View for Agent Model
    """
    form_columns = ['uuid', 'agent_port', 'node']
    column_list = ['uuid', 'device_uuid', 'device_xml', 'agent_port', 'container', 'node', 'status']
    column_labels = {'uuid': 'Agent UUID',
                     'device_xml': 'Device xml model',
                     'device_uuid': 'Device UUID'}
