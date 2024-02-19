from flask_admin.contrib.sqla import ModelView


class AgentView(ModelView):
    form_columns = ['uuid', 'agent_port', 'node']
    column_list = ['uuid', 'device_uuid', 'agent_port', 'container', 'node', 'status']
    column_labels = {'uuid': 'Agent UUID',
                     'device_uuid': 'Device UUID'}
