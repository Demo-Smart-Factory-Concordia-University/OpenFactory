"""
User notifcations emmited by the OpenFactory models
"""


class UserNotifications:

    success = print
    fail = print
    info = print

    def setup(self, success_msg, fail_msg, info_msg):
        self.success = success_msg
        self.fail = fail_msg
        self.info = info_msg


user_notify = UserNotifications()
