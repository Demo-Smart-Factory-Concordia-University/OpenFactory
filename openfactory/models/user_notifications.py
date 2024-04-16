"""
User notifcations emmited by the OpenFactory models
"""


class UserNotifcations:

    success = print
    fail = print

    def setup(self, success_msg, fail_msg):
        self.success = success_msg
        self.fail = fail_msg


user_notify = UserNotifcations()
