from flask_admin.contrib.sqla import ModelView


class NotificationView(ModelView):
    """
    Admin View for User Notification Model
    """
    can_create = False
    can_edit = False

    form_columns = ['user', 'message', 'type']
    column_list = ['id', 'user', 'message', 'type']
