from flask_admin.contrib.sqla import ModelView


class NotificationView(ModelView):
    """
    Admin View for User Notification Model
    """
    form_columns = ['user', 'message', 'type']
    column_list = ['id', 'user', 'message', 'type']
