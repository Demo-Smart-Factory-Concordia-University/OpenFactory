from flask_admin.contrib.sqla import ModelView
from flask_admin.form import SecureForm
from wtforms import PasswordField


class UserAdmin(ModelView):
    """ Admin View of users """
    form_base_class = SecureForm
    form_excluded_columns = ('password_hash')
    form_extra_fields = {
        'password': PasswordField('Password')
    }

    column_exclude_list = ['password_hash', ]

    def on_model_change(self, form, User, is_created):
        if form.password.data is not None:
            User.set_password(form.password.data)
