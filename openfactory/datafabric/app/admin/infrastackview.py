from flask_admin.contrib.sqla import ModelView


class InfraStackView(ModelView):
    """
    Admin View for InfraStack Model
    """
    form_columns = ['stack_name', 'nodes']
    column_list = ['id', 'stack_name', 'nodes']
