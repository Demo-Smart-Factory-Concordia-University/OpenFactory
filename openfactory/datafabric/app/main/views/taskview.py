from flask_admin.contrib.sqla import ModelView


class RQTaskView(ModelView):
    """
    Admin View for RQ Task Model
    """
    form_columns = ['id', 'name', 'description', 'user', 'complete']
    column_list = ['id', 'name', 'description', 'user', 'complete']
    column_labels = {'id': 'RQ ID',
                     'user': 'Task Owner'}
