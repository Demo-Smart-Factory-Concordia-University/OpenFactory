from flask_admin.contrib.sqla import ModelView


class ComposeProjectView(ModelView):
    """
    Admin View for ComposeProject Model
    """
    form_columns = ['name', 'description', 'yaml_config', 'node']
    column_list = ['id', 'name', 'description', 'node']
    column_labels = {'id': 'Project Name',
                     'Description': 'Node'}
