from flask_admin.contrib.sqla import ModelView


class NotificationView(ModelView):
    """
    Admin View for User Notification Model
    """
    form_columns = ['user', 'message']
    column_list = ['id', 'user', 'message']
