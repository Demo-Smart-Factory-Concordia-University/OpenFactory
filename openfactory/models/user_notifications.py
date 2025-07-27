""" User notifcations emmited by the OpenFactory models. """


class UserNotifications:
    """ Notification dispatcher for user-facing messages. """

    success = print
    fail = print
    info = print
    warning = print

    def setup(self, success_msg: callable, fail_msg: callable, info_msg: callable, warning_msg: callable) -> None:
        """
        Configure custom notification handlers.

        Args:
            success_msg (Callable): Function to call for success messages.
            fail_msg (Callable): Function to call for failure messages.
            info_msg (Callable): Function to call for informational messages.
            warning_msg (Callable): Function to call for warning messages.
        """
        self.success = success_msg
        self.fail = fail_msg
        self.info = info_msg
        self.warning = warning_msg


user_notify = UserNotifications()
